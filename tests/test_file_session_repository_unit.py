"""Automated tests for file-backed session repository persistence robustness."""

import json

import pytest

from moyuan_web.repositories.file_session_repository import FileSessionRepository


@pytest.mark.asyncio
async def test_file_session_repository_writes_primary_and_backup(tmp_path):
    repository_path = tmp_path / "sessions.json"
    repository = FileSessionRepository(str(repository_path))

    session_id = await repository.create({"session_id": "s1", "messages": []})

    backup_path = tmp_path / f"sessions.json{FileSessionRepository.BACKUP_SUFFIX}"
    assert session_id == "s1"
    assert repository_path.exists()
    assert backup_path.exists()

    backup_snapshot = json.loads(backup_path.read_text(encoding="utf-8"))
    assert "s1" in backup_snapshot


@pytest.mark.asyncio
async def test_file_session_repository_recovers_from_backup_when_primary_corrupted(tmp_path):
    repository_path = tmp_path / "sessions.json"
    repository = FileSessionRepository(str(repository_path))
    await repository.create(
        {
            "session_id": "s1",
            "messages": [{"role": "user", "content": "hello"}],
        }
    )

    # Simulate interrupted write on primary file.
    repository_path.write_text("{invalid-json", encoding="utf-8")

    recovered = FileSessionRepository(str(repository_path))
    loaded = await recovered.get("s1")
    assert loaded is not None
    assert loaded.get("session_id") == "s1"

    repaired_snapshot = json.loads(repository_path.read_text(encoding="utf-8"))
    assert "s1" in repaired_snapshot
