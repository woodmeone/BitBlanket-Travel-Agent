"""Unit tests for the SQL-backed checkpoint saver."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage

from agent.travel_agent.graph.builder import build_travel_agent
from agent.travel_agent.graph.postgres_checkpointer import PersistentPostgresSaver
from agent.travel_agent.graph.state import TRAVEL_AGENT_SYSTEM_PROMPT, create_initial_state


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


def test_persistent_postgres_saver_recovers_multi_turn_session(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'checkpoint-recovery.db'}"
    session_id = "postgres-recovery-session"

    saver_1 = PersistentPostgresSaver(database_url)
    agent_1 = build_travel_agent(
        llm=FakeLLM(),
        tools=[],
        system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=saver_1,
    )
    result_1 = agent_1.invoke(
        create_initial_state(
            user_message="先给我一个周末城市建议",
            session_id=session_id,
            system_message=TRAVEL_AGENT_SYSTEM_PROMPT,
        )
    )
    assert result_1.get("answer")

    config = {"configurable": {"thread_id": session_id}}
    assert saver_1.get_tuple(config) is not None

    saver_2 = PersistentPostgresSaver(database_url)
    assert saver_2.get_tuple(config) is not None

    agent_2 = build_travel_agent(
        llm=FakeLLM(),
        tools=[],
        system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=saver_2,
    )
    result_2 = agent_2.invoke(
        create_initial_state(
            user_message="再给一个预算友好的选项",
            session_id=session_id,
            system_message=TRAVEL_AGENT_SYSTEM_PROMPT,
        )
    )
    assert result_2.get("answer")
    assert len(list(saver_2.list(config))) >= 2


def test_persistent_postgres_saver_compacts_recent_only(tmp_path: Path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'checkpoint-compaction.db'}"
    saver = PersistentPostgresSaver(
        database_url,
        max_checkpoints_per_thread_ns=3,
        compaction_interval=1,
    )
    session_id = "postgres-compact-session"
    agent = build_travel_agent(
        llm=FakeLLM(),
        tools=[],
        system_prompt=TRAVEL_AGENT_SYSTEM_PROMPT,
        checkpointer=saver,
    )

    for idx in range(8):
        agent.invoke(
            create_initial_state(
                user_message=f"message-{idx}",
                session_id=session_id,
                system_message=TRAVEL_AGENT_SYSTEM_PROMPT,
            )
        )

    assert saver.get_checkpoint_count(session_id) <= 3
