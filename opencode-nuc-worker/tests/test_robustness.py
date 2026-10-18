"""Robustness tests for StateDB and OpenCodeNUCWorker (Mission 2 — F1/F2).

10 tests covering idempotence, state transitions, error handling, and
concurrent-claim protection for the SQLite-backed state machine.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from opencode_nuc_worker import (
    GitHubRequest, WorkerConfig, StateDB, OpenCodeNUCWorker,
    GitHubRestClient, OpenCodeExecutor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_comment(request_id: str, login: str = "tvnv",
                  repo: str = "tvnv/axon-orchestrator") -> dict:
    body = json.dumps({"request_id": request_id, "repo": repo,
                       "mission": {"id": request_id}})
    return {
        "id": hash(request_id) & 0xFFFFFF,
        "body": f"REQUEST: {body}",
        "user": {"login": login, "id": 1},
        "repository": {"full_name": repo},
        "created_at": "2026-10-19T00:00:00Z",
        "branch": "dev",
    }


def _make_worker(tmp_path, *, authors=("tvnv",), executor=None):
    config = WorkerConfig(
        github_token="fake",
        allowed_authors=list(authors),
        allowed_repos=["tvnv/axon-orchestrator"],
    )
    db = StateDB(str(tmp_path / "state.db"))
    mock_client = Mock(spec=GitHubRestClient)
    mock_client.get_issue_comments.return_value = []
    mock_client.create_comment.return_value = {"id": 42}
    if executor is None:
        executor = Mock(spec=OpenCodeExecutor)
        executor.execute.return_value = Mock(
            ok=True, exit_code=0, stdout_tail="ok",
            stderr_tail="", duration_seconds=1, request_id="r"
        )
    worker = OpenCodeNUCWorker(config, Mock(), db, executor)
    worker.client = mock_client
    return worker, db, mock_client


# ===========================================================================
# 1. StateDB: new request_id → claim succeeds
# ===========================================================================

def test_statedb_claim_new(tmp_path):
    db = StateDB(str(tmp_path / "state.db"))
    assert db.claim_or_retry("req-1") is True
    assert db.get_state("req-1") == "CLAIMED"


# ===========================================================================
# 2. StateDB: same request_id twice → second claim fails (RUNNING guard)
# ===========================================================================

def test_statedb_claim_running_blocks(tmp_path):
    db = StateDB(str(tmp_path / "state.db"))
    db.claim_or_retry("req-2")
    db.mark_running("req-2")
    assert db.claim_or_retry("req-2") is False


# ===========================================================================
# 3. StateDB: CLAIMED without running_at → retryable after crash
# ===========================================================================

def test_statedb_claimed_without_running_is_retryable(tmp_path):
    db = StateDB(str(tmp_path / "state.db"))
    assert db.claim_or_retry("req-3") is True   # CLAIMED, running_at=NULL
    # Simulate restart: a second claim_or_retry on a CLAIMED-no-running row is allowed
    assert db.claim_or_retry("req-3") is True


# ===========================================================================
# 4. StateDB: COMPLETED → claim blocked
# ===========================================================================

def test_statedb_completed_blocks_claim(tmp_path):
    db = StateDB(str(tmp_path / "state.db"))
    db.claim_or_retry("req-4")
    db.mark_running("req-4")
    db.mark_completed("req-4", {"success": True}, comment_id=7)
    assert db.claim_or_retry("req-4") is False
    assert db.get_state("req-4") == "COMPLETED"


# ===========================================================================
# 5. StateDB: FAILED → claim blocked (no auto-retry of failed requests)
# ===========================================================================

def test_statedb_failed_blocks_claim(tmp_path):
    db = StateDB(str(tmp_path / "state.db"))
    db.claim_or_retry("req-5")
    db.mark_running("req-5")
    db.mark_failed("req-5", {"error": "timeout"})
    assert db.claim_or_retry("req-5") is False
    assert db.get_state("req-5") == "FAILED"


# ===========================================================================
# 6. StateDB: migrate_from_jsonl imports COMPLETED entries
# ===========================================================================

def test_statedb_migrate_jsonl(tmp_path):
    jsonl = tmp_path / "results.jsonl"
    jsonl.write_text(
        json.dumps({
            "request_id": "old-smoke",
            "recorded_at": "2026-10-18T22:34:55Z",
            "outcome": {"success": True, "exit_code": 0, "duration_seconds": 75},
        }) + "\n"
    )
    db = StateDB(str(tmp_path / "state.db"))
    n = db.migrate_from_jsonl(str(jsonl))
    assert n == 1
    assert db.get_state("old-smoke") == "COMPLETED"
    assert db.claim_or_retry("old-smoke") is False  # already done — blocked


# ===========================================================================
# 7. Worker: same request_id in consecutive polls → execute called once
# ===========================================================================

def test_worker_no_double_execution(tmp_path):
    worker, db, mock_client = _make_worker(tmp_path)
    comment = _make_comment("idem-req")
    mock_client.get_issue_comments.side_effect = [
        [comment],
        [comment],  # same comment seen again
    ]
    worker.poll_once()
    assert db.get_state("idem-req") == "COMPLETED"
    worker.poll_once()
    assert worker.executor.execute.call_count == 1


# ===========================================================================
# 8. Worker: _publish_result not called twice if already COMPLETED with comment_id
# ===========================================================================

def test_worker_result_not_double_published(tmp_path):
    worker, db, mock_client = _make_worker(tmp_path)
    # Pre-populate a COMPLETED entry with a comment_id
    db.claim_or_retry("already-done")
    db.mark_running("already-done")
    db.mark_completed("already-done", {"success": True}, comment_id=99)

    # Call _publish_result directly — should return existing comment_id without posting
    request = GitHubRequest(
        request_id="already-done", author="tvnv", author_login="tvnv",
        repo="tvnv/axon-orchestrator", branch="dev",
        mission={"id": "already-done"}, created_at="2026-10-19T00:00:00Z",
    )
    returned_id = worker._publish_result(request, {"success": True, "exit_code": 0,
                                                    "duration_seconds": 1,
                                                    "stdout": "", "stderr": ""})
    assert returned_id == 99
    mock_client.create_comment.assert_not_called()


# ===========================================================================
# 9. Worker: mark_failed called when executor raises an exception
# ===========================================================================

def test_worker_mark_failed_on_executor_exception(tmp_path):
    bad_executor = Mock(spec=OpenCodeExecutor)
    bad_executor.execute.side_effect = RuntimeError("opencode crashed")

    worker, db, mock_client = _make_worker(tmp_path, executor=bad_executor)
    comment = _make_comment("crash-req")
    mock_client.get_issue_comments.return_value = [comment]

    worker.poll_once()

    assert db.get_state("crash-req") == "FAILED"
    outcome = db.get_outcome("crash-req")
    assert outcome is not None
    assert "opencode crashed" in outcome.get("error", "")


# ===========================================================================
# 10. Worker: OpenCode timeout (ok=False) → state becomes FAILED
# ===========================================================================

def test_worker_mark_failed_on_opencode_timeout(tmp_path):
    timeout_executor = Mock(spec=OpenCodeExecutor)
    timeout_executor.execute.return_value = Mock(
        ok=False, exit_code=-1, stdout_tail="",
        stderr_tail="OpenCode exceeded lease window", duration_seconds=300,
        request_id="timeout-req",
    )

    worker, db, mock_client = _make_worker(tmp_path, executor=timeout_executor)
    comment = _make_comment("timeout-req")
    mock_client.get_issue_comments.return_value = [comment]

    worker.poll_once()

    assert db.get_state("timeout-req") == "FAILED"
    outcome = db.get_outcome("timeout-req")
    assert outcome is not None
    assert outcome.get("success") is False
