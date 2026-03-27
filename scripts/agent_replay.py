"""Checkpoint replay utility for failure reproduction and incident analysis."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from langchain_core.messages import BaseMessage, HumanMessage

if __package__:
    from .bootstrap_paths import PROJECT_ROOT as ROOT, ensure_project_paths
else:  # pragma: no cover - direct script execution / spec-loaded module path
    _bootstrap_path = Path(__file__).with_name("bootstrap_paths.py")
    _bootstrap_spec = importlib.util.spec_from_file_location("scripts.bootstrap_paths", _bootstrap_path)
    if _bootstrap_spec is None or _bootstrap_spec.loader is None:
        raise ImportError(f"Cannot load bootstrap helper from {_bootstrap_path}")
    _bootstrap_module = importlib.util.module_from_spec(_bootstrap_spec)
    _bootstrap_spec.loader.exec_module(_bootstrap_module)
    ROOT = _bootstrap_module.PROJECT_ROOT
    ensure_project_paths = _bootstrap_module.ensure_project_paths

ensure_project_paths()

from agent.travel_agent.graph.builder import build_travel_agent
from agent.travel_agent.graph.persistent_checkpointer import PersistentSqliteSaver
from agent.travel_agent.graph.state import TRAVEL_AGENT_SYSTEM_PROMPT, create_initial_state
from agent.travel_agent.llm.langchain_adapter import create_from_yaml_config
from agent.travel_agent.tools.travel_tools import get_travel_tools


def _build_config(session_id: str, checkpoint_ns: str, checkpoint_id: str | None = None) -> dict[str, Any]:
    """Build LangGraph configurable context for checkpoint access."""
    configurable: dict[str, Any] = {"thread_id": session_id, "checkpoint_ns": checkpoint_ns}
    if checkpoint_id:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def _message_text(message: Any) -> str:
    """Normalize different message payload shapes into plain text."""
    if isinstance(message, BaseMessage):
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "".join(parts)
        if isinstance(content, dict):
            text = content.get("text")
            return str(text) if text is not None else ""
        return str(content)
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "".join(parts)
        return str(content or "")
    return str(message or "")


def extract_latest_user_message(messages: Iterable[Any]) -> str:
    """Extract latest non-empty user/human message from checkpoint history."""
    message_list = list(messages or [])
    for item in reversed(message_list):
        if isinstance(item, HumanMessage):
            text = _message_text(item).strip()
            if text:
                return text
            continue

        if isinstance(item, BaseMessage):
            role = str(getattr(item, "type", "")).lower()
            if role in {"human", "user"}:
                text = _message_text(item).strip()
                if text:
                    return text
            continue

        if isinstance(item, dict):
            role = str(item.get("role") or item.get("type") or "").lower()
            if role in {"human", "user"}:
                text = _message_text(item).strip()
                if text:
                    return text
    return ""


def _build_failure_distribution(execution_summary: dict[str, Any], execution_stats: dict[str, Any]) -> dict[str, int]:
    """Return normalized failure-code histogram from summary or execution steps."""
    summary_distribution = execution_summary.get("error_code_distribution")
    if isinstance(summary_distribution, dict):
        normalized: dict[str, int] = {}
        for key, value in summary_distribution.items():
            normalized[str(key)] = int(value or 0)
        return normalized

    counter: Counter[str] = Counter()
    steps = execution_stats.get("steps", []) if isinstance(execution_stats, dict) else []
    if not isinstance(steps, list):
        return {}

    for item in steps:
        if not isinstance(item, dict):
            continue
        code = item.get("error_code")
        if code:
            counter[str(code)] += 1
    return dict(counter)


def load_checkpoint_source(
    session_id: str,
    db_path: str,
    checkpoint_ns: str = "",
    checkpoint_id: str | None = None,
) -> dict[str, Any]:
    """Load checkpoint snapshot and normalize replay source metadata."""
    saver = PersistentSqliteSaver(db_path)

    if checkpoint_id:
        checkpoint_tuple = saver.get_tuple(_build_config(session_id, checkpoint_ns, checkpoint_id))
    else:
        latest = list(saver.list(_build_config(session_id, checkpoint_ns), limit=1))
        checkpoint_tuple = latest[0] if latest else None

    if checkpoint_tuple is None:
        raise ValueError(
            f"Checkpoint not found for session_id={session_id}, checkpoint_ns={checkpoint_ns}, checkpoint_id={checkpoint_id or 'latest'}"
        )

    config = checkpoint_tuple.config or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    checkpoint = checkpoint_tuple.checkpoint or {}
    channel_values = checkpoint.get("channel_values", {}) if isinstance(checkpoint, dict) else {}
    if not isinstance(channel_values, dict):
        channel_values = {}

    messages = channel_values.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    execution_summary = channel_values.get("execution_summary", {})
    if not isinstance(execution_summary, dict):
        execution_summary = {}

    execution_stats = channel_values.get("execution_stats", {})
    if not isinstance(execution_stats, dict):
        execution_stats = {}

    failure_code_distribution = _build_failure_distribution(execution_summary, execution_stats)
    plan = channel_values.get("plan", [])
    if not isinstance(plan, list):
        plan = []

    tools_used = channel_values.get("tools_used", [])
    if not isinstance(tools_used, list):
        tools_used = []

    return {
        "session_id": str(configurable.get("thread_id") or session_id),
        "checkpoint_ns": str(configurable.get("checkpoint_ns") or checkpoint_ns),
        "checkpoint_id": str(configurable.get("checkpoint_id") or ""),
        "checkpoint_ts": checkpoint.get("ts") if isinstance(checkpoint, dict) else None,
        "intent": channel_values.get("intent"),
        "routing": channel_values.get("routing"),
        "plan_id": channel_values.get("plan_id"),
        "plan": plan,
        "tools_used": tools_used,
        "execution_summary": execution_summary,
        "failure_code_distribution": failure_code_distribution,
        "message_count": len(messages),
        "user_message": extract_latest_user_message(messages),
    }


async def run_replay(
    user_message: str,
    session_id: str,
    llm_config_path: str,
) -> dict[str, Any]:
    """Re-execute one user prompt through live runtime and capture replay metrics."""
    started = time.perf_counter()
    try:
        llm_adapter = create_from_yaml_config(llm_config_path)
        llm = llm_adapter.chat_model
        tools = get_travel_tools()
        agent = build_travel_agent(
            llm=llm,
            tools=tools,
            system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
        )
        state = create_initial_state(
            user_message=user_message,
            session_id=session_id,
            system_message=TRAVEL_AGENT_SYSTEM_PROMPT,
            run_id=f"replay-{int(time.time())}",
        )
        result = await agent.ainvoke(state)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        execution_summary = result.get("execution_summary", {})
        if not isinstance(execution_summary, dict):
            execution_summary = {}
        execution_stats = result.get("execution_stats", {})
        if not isinstance(execution_stats, dict):
            execution_stats = {}
        return {
            "success": True,
            "elapsed_ms": elapsed_ms,
            "intent": result.get("intent"),
            "routing": result.get("routing"),
            "plan_id": result.get("plan_id"),
            "tools_used": list(result.get("tools_used", []) or []),
            "answer": str(result.get("answer") or ""),
            "execution_summary": execution_summary,
            "failure_code_distribution": _build_failure_distribution(execution_summary, execution_stats),
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "success": False,
            "elapsed_ms": elapsed_ms,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }


async def generate_replay_report(
    session_id: str,
    db_path: str,
    checkpoint_id: str | None,
    checkpoint_ns: str,
    llm_config_path: str,
    dry_run: bool,
    message_override: str | None,
) -> dict[str, Any]:
    """Generate combined source snapshot and replay result payload."""
    source = load_checkpoint_source(
        session_id=session_id,
        db_path=db_path,
        checkpoint_ns=checkpoint_ns,
        checkpoint_id=checkpoint_id,
    )

    replay_message = (message_override or source.get("user_message") or "").strip()
    if not replay_message:
        raise ValueError("No user message available for replay. Provide --message to override.")
    source["replay_message"] = replay_message

    if dry_run:
        replay: dict[str, Any] = {
            "success": None,
            "dry_run": True,
            "skipped": True,
            "reason": "dry_run_enabled",
        }
    else:
        replay = await run_replay(
            user_message=replay_message,
            session_id=session_id,
            llm_config_path=llm_config_path,
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "replay": replay,
    }


def _sanitize_file_stem(value: str) -> str:
    """Sanitize dynamic session text for safe filesystem filename usage."""
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", value)
    return (text.strip("_") or "session")[:60]


def write_report(report: dict[str, Any], output_dir: Path, session_id: str) -> tuple[Path, Path]:
    """Persist replay report as timestamped JSON and Markdown artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"agent_replay_{_sanitize_file_stem(session_id)}_{timestamp}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    source = report.get("source", {}) if isinstance(report, dict) else {}
    replay = report.get("replay", {}) if isinstance(report, dict) else {}
    execution_summary = source.get("execution_summary", {}) if isinstance(source, dict) else {}

    lines = [
        "# Agent Checkpoint Replay Report",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- session_id: {source.get('session_id')}",
        f"- checkpoint_id: {source.get('checkpoint_id')}",
        f"- checkpoint_ns: {source.get('checkpoint_ns')}",
        f"- checkpoint_ts: {source.get('checkpoint_ts')}",
        f"- intent: {source.get('intent')}",
        f"- routing: {source.get('routing')}",
        f"- plan_id: {source.get('plan_id')}",
        f"- plan_steps: {len(source.get('plan', []) or [])}",
        f"- message_count: {source.get('message_count')}",
        "",
        "## Source Snapshot",
        "",
        f"- replay_message: {source.get('replay_message')}",
        f"- tools_used: {source.get('tools_used', [])}",
        f"- success_steps: {execution_summary.get('success_steps', 0)}",
        f"- failed_steps: {execution_summary.get('failed_steps', 0)}",
        f"- blocked_steps: {execution_summary.get('blocked_steps', 0)}",
        f"- failure_code_distribution: {source.get('failure_code_distribution', {})}",
        "",
        "## Replay Result",
        "",
    ]

    if replay.get("dry_run"):
        lines.extend(
            [
                "- mode: dry-run",
                f"- reason: {replay.get('reason')}",
            ]
        )
    else:
        lines.extend(
            [
                f"- success: {replay.get('success')}",
                f"- elapsed_ms: {replay.get('elapsed_ms')}",
                f"- intent: {replay.get('intent')}",
                f"- routing: {replay.get('routing')}",
                f"- plan_id: {replay.get('plan_id')}",
                f"- tools_used: {replay.get('tools_used', [])}",
                f"- failure_code_distribution: {replay.get('failure_code_distribution', {})}",
            ]
        )
        answer = str(replay.get("answer") or "").strip()
        if answer:
            lines.extend(["", "### Answer Preview", "", answer[:600]])
        error = replay.get("error")
        if error:
            lines.extend(["", "### Error", "", str(error)])

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for replay utility."""
    parser = argparse.ArgumentParser(description="Replay failed agent session from LangGraph checkpoint.")
    parser.add_argument("--session-id", required=True, help="Session ID (LangGraph thread_id).")
    parser.add_argument(
        "--db",
        default=str(ROOT / "data" / "langgraph_checkpoints.sqlite3"),
        help="Path to checkpoint sqlite database.",
    )
    parser.add_argument("--checkpoint-id", default=None, help="Specific checkpoint ID. Default: latest checkpoint.")
    parser.add_argument("--checkpoint-ns", default="", help="Checkpoint namespace.")
    parser.add_argument(
        "--llm-config",
        default=str(ROOT / "config" / "llm_config.yaml"),
        help="LLM config YAML path used for replay execution.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "docs" / "benchmarks"),
        help="Directory for replay reports (json + md).",
    )
    parser.add_argument(
        "--message",
        default=None,
        help="Override replay user message (defaults to latest user message in checkpoint).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only export source checkpoint snapshot without replay execution.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for checkpoint replay report generation."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = asyncio.run(
            generate_replay_report(
                session_id=str(args.session_id),
                db_path=str(args.db),
                checkpoint_id=str(args.checkpoint_id) if args.checkpoint_id else None,
                checkpoint_ns=str(args.checkpoint_ns or ""),
                llm_config_path=str(args.llm_config),
                dry_run=bool(args.dry_run),
                message_override=str(args.message) if args.message else None,
            )
        )
    except Exception as exc:
        print(f"Replay report generation failed: {exc}", file=sys.stderr)
        return 1

    json_path, md_path = write_report(report, Path(args.output_dir), str(args.session_id))
    print(f"Replay JSON report: {json_path}")
    print(f"Replay Markdown report: {md_path}")

    replay = report.get("replay", {})
    if isinstance(replay, dict) and replay.get("success") is False:
        print(f"Replay execution failed: {replay.get('error_type')}: {replay.get('error')}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
