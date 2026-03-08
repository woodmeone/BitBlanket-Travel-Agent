from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.src.graph.builder import build_travel_agent
from agent.src.graph.persistent_checkpointer import PersistentSqliteSaver
from agent.src.graph.state import TRAVEL_AGENT_SYSTEM_PROMPT, create_initial_state


def _load_replay_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "agent_replay.py"
    spec = importlib.util.spec_from_file_location("agent_replay", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _StructuredIntentLLM:
    def __init__(self, schema):
        self._schema = schema

    def invoke(self, _messages):
        return self._schema(
            intent="general",
            confidence=1.0,
            entities={},
            requires_tools=False,
        )


class FakeLLM:
    def bind_tools(self, _tools):
        return self

    def with_structured_output(self, schema, method=None):  # noqa: ARG002
        return _StructuredIntentLLM(schema)

    def invoke(self, _messages):
        return AIMessage(content="ok")


def _seed_checkpoint(db_path: Path, session_id: str, user_message: str) -> None:
    saver = PersistentSqliteSaver(str(db_path))
    agent = build_travel_agent(
        llm=FakeLLM(),
        tools=[],
        system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=saver,
    )
    result = agent.invoke(
        create_initial_state(
            user_message=user_message,
            session_id=session_id,
            system_message=TRAVEL_AGENT_SYSTEM_PROMPT,
        )
    )
    assert result.get("answer")


def test_extract_latest_user_message_prefers_latest_human_message():
    replay = _load_replay_module()
    messages = [
        HumanMessage(content="first"),
        AIMessage(content="assistant"),
        {"role": "user", "content": "second"},
        AIMessage(content="assistant-2"),
        HumanMessage(content="latest"),
    ]
    assert replay.extract_latest_user_message(messages) == "latest"


def test_generate_replay_report_dry_run_and_write_files(tmp_path: Path):
    replay = _load_replay_module()
    db_path = tmp_path / "langgraph_checkpoints.sqlite3"
    session_id = "replay-dryrun-session"
    _seed_checkpoint(db_path, session_id, "给我一个周末城市建议")

    report = asyncio.run(
        replay.generate_replay_report(
            session_id=session_id,
            db_path=str(db_path),
            checkpoint_id=None,
            checkpoint_ns="",
            llm_config_path=str(tmp_path / "missing-config.yaml"),
            dry_run=True,
            message_override=None,
        )
    )

    assert report.get("generated_at")
    assert report.get("source", {}).get("session_id") == session_id
    assert report.get("source", {}).get("replay_message")
    assert report.get("replay", {}).get("dry_run") is True

    json_path, md_path = replay.write_report(report, tmp_path, session_id)
    assert json_path.exists()
    assert md_path.exists()
    assert "Agent Checkpoint Replay Report" in md_path.read_text(encoding="utf-8")


def test_generate_replay_report_raises_when_no_user_message(monkeypatch):
    replay = _load_replay_module()

    monkeypatch.setattr(
        replay,
        "load_checkpoint_source",
        lambda **_kwargs: {
            "session_id": "empty-session",
            "checkpoint_ns": "",
            "checkpoint_id": "cp-empty",
            "checkpoint_ts": None,
            "intent": None,
            "routing": None,
            "plan_id": None,
            "plan": [],
            "tools_used": [],
            "execution_summary": {},
            "failure_code_distribution": {},
            "message_count": 0,
            "user_message": "",
        },
    )

    with pytest.raises(ValueError, match="No user message available for replay"):
        asyncio.run(
            replay.generate_replay_report(
                session_id="empty-session",
                db_path="unused.sqlite3",
                checkpoint_id=None,
                checkpoint_ns="",
                llm_config_path="unused.yaml",
                dry_run=True,
                message_override=None,
            )
        )


def test_main_returns_nonzero_for_missing_session(tmp_path: Path):
    replay = _load_replay_module()
    db_path = tmp_path / "empty.sqlite3"
    PersistentSqliteSaver(str(db_path))

    exit_code = replay.main(
        [
            "--session-id",
            "not-found-session",
            "--db",
            str(db_path),
            "--dry-run",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 1
