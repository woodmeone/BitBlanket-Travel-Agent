import pytest
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage

from agent.src.graph.memory_integration import AgentMemoryManager


@pytest.mark.asyncio
async def test_memory_cleanup_expired_sessions():
    manager = AgentMemoryManager(
        max_history=5,
        summary_threshold=5,
        persist_path=None,
        session_ttl_seconds=1,
        max_sessions=10,
    )

    await manager.add_message("s1", "user", "hello")
    await manager.add_message("s2", "user", "world")

    # Force s1 to be expired.
    manager._sessions["s1"]["messages"][-1].timestamp = "2000-01-01T00:00:00"

    # Any async API call triggers cleanup.
    await manager.get_summary("s2")

    assert "s1" not in manager._sessions
    assert "s2" in manager._sessions


@pytest.mark.asyncio
async def test_memory_capacity_evicts_old_sessions():
    manager = AgentMemoryManager(
        max_history=5,
        summary_threshold=5,
        persist_path=None,
        session_ttl_seconds=3600,
        max_sessions=2,
    )

    await manager.add_message("s1", "user", "first")
    await manager.add_message("s2", "user", "second")

    # Make s1 oldest.
    now = datetime.now()
    manager._sessions["s1"]["messages"][-1].timestamp = (now - timedelta(seconds=10)).isoformat()
    manager._sessions["s2"]["messages"][-1].timestamp = (now - timedelta(seconds=5)).isoformat()

    await manager.add_message("s3", "user", "third")

    assert len(manager._sessions) == 2
    assert "s1" not in manager._sessions
    assert "s2" in manager._sessions
    assert "s3" in manager._sessions


@pytest.mark.asyncio
async def test_memory_profile_extraction_from_user_messages():
    manager = AgentMemoryManager(
        max_history=5,
        summary_threshold=5,
        persist_path=None,
        session_ttl_seconds=3600,
        max_sessions=10,
    )

    await manager.add_message("s1", "user", "两个人，预算5000元，玩4天，偏好美食和历史，避免人多")
    profile = await manager.get_profile("s1")

    assert profile.get("people_hint") == 2
    assert profile.get("days_hint") == 4
    assert profile.get("budget_hint") in {"5000元", "5000人民币"}
    assert "美食" in profile.get("interests", [])
    assert "历史" in profile.get("interests", [])
    assert "人多" in profile.get("avoid_preferences", [])
    assert profile.get("schema_version") == 2
    assert "_meta" in profile


@pytest.mark.asyncio
async def test_memory_clear_and_delete_session():
    manager = AgentMemoryManager(
        max_history=5,
        summary_threshold=2,
        persist_path=None,
        session_ttl_seconds=3600,
        max_sessions=10,
    )
    await manager.add_message("s1", "user", "预算3000元，玩2天")
    await manager.add_message("s1", "assistant", "world")

    cleared = await manager.clear_session_messages("s1")
    assert cleared is True
    assert await manager.get_recent_messages("s1") == []
    assert await manager.get_summary("s1") == ""
    cleared_profile = await manager.get_profile("s1")
    assert cleared_profile.get("schema_version") == 2
    assert cleared_profile.get("interests") == []

    deleted = await manager.delete_session("s1")
    assert deleted is True
    assert await manager.get_recent_messages("s1") == []


@pytest.mark.asyncio
async def test_memory_context_clipping_prefers_relevant_messages():
    manager = AgentMemoryManager(
        max_history=4,
        summary_threshold=10,
        persist_path=None,
        session_ttl_seconds=3600,
        max_sessions=10,
    )

    await manager.add_message("s1", "user", "我在上海出差，住在陆家嘴")
    await manager.add_message("s1", "assistant", "好的，记录上海行程")
    await manager.add_message("s1", "user", "我也在关注北京景点")
    await manager.add_message("s1", "assistant", "北京故宫和颐和园值得去")

    context = manager.build_context_messages_for_query("s1", "北京三日游怎么玩", max_messages=2)
    user_context = [m for m in context if isinstance(m, HumanMessage)]
    assert any("北京" in m.content for m in user_context)


@pytest.mark.asyncio
async def test_memory_conflict_detection_adds_pending_clarification():
    manager = AgentMemoryManager(
        max_history=5,
        summary_threshold=5,
        persist_path=None,
        session_ttl_seconds=3600,
        max_sessions=10,
    )

    await manager.add_message("s1", "user", "预算3000元，两个人")
    await manager.add_message("s1", "user", "这次预算10000元")
    profile = await manager.get_profile("s1")
    pending = profile.get("pending_clarifications", [])
    assert isinstance(pending, list)
    assert pending
    assert "预算偏好" in str(pending[0].get("prompt", ""))
    assert str(profile.get("budget_hint", "")).startswith("3000")


@pytest.mark.asyncio
async def test_memory_profile_time_decay_filters_old_attributes():
    manager = AgentMemoryManager(
        max_history=5,
        summary_threshold=5,
        persist_path=None,
        session_ttl_seconds=3600 * 24 * 365,
        max_sessions=10,
    )

    await manager.add_message("s1", "user", "预算5000元，3天")
    attrs = manager._sessions["s1"]["profile"]["attributes"]
    for item in attrs.values():
        item["updated_at"] = "2020-01-01T00:00:00"

    profile = await manager.get_profile("s1")
    assert "budget_hint" not in profile
    meta = profile.get("_meta", {})
    assert "budget_hint" in meta
    assert meta["budget_hint"].get("decayed_confidence", 1.0) < manager.MIN_DECAY_CONFIDENCE
