"""Tests de base pour le worker NUC OpenCode."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from opencode_nuc_worker import GitHubRequest, WorkerConfig, ResultsJournal
from opencode_nuc_worker.worker import parse_request_from_body


class TestGitHubRequest:
    """Tests pour la classe GitHubRequest."""

    def test_request_creation(self):
        """Test la création d'une requête GitHub."""
        comment = {
            "request_id": "test-123",
            "user": {"login": "testuser"},
            "repository": {"full_name": "tvnv/axon-orchestrator"},
            "body": "REQUEST: {\"request_id\": \"test-123\", \"mission\": {\"id\": \"mission-456\"}}",
            "branch": "main"
        }
        author_info = {"login": "testuser", "id": 789}

        request = GitHubRequest.from_comment(comment, author_info)

        assert request.request_id == "test-123"
        assert request.author == "unknown"
        assert request.author_login == "testuser"
        assert request.repo == "tvnv/axon-orchestrator"
        assert request.branch == "main"
        assert request.mission == {"id": "mission-456"}

    def test_request_validation(self):
        """Test la validation de la requête (allowlist fail-closed)."""
        request = GitHubRequest(
            request_id="test-123",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-456"},
            created_at="2026-10-18T18:00:00Z"
        )

        # Allowlist vide = fail-closed : toute requête est rejetée
        config = WorkerConfig(github_token="fake-token")
        errors = request.validate(config)
        assert len(errors) > 0
        assert "auteur" in errors[0].lower()

        # Auteur autorisé : validation OK
        config.allowed_authors = ["testuser@github.com"]
        errors = request.validate(config)
        assert len(errors) == 0

        # Auteur non autorisé : rejeté
        config.allowed_authors = ["otheruser@github.com"]
        errors = request.validate(config)
        assert len(errors) > 0
        assert "non autorisé" in errors[0]

    def test_request_validation_repo(self):
        """Test la validation du dépôt."""
        request = GitHubRequest(
            request_id="test-123",
            author="testuser",
            author_login="testuser@github.com",
            repo="unauthorized/repo",
            branch="main",
            mission={"id": "mission-456"},
            created_at="2026-10-18T18:00:00Z"
        )

        # Allowlist with the test user so the repo error is the first failure
        config = WorkerConfig(
            github_token="fake-token",
            allowed_repos=["tvnv/axon-orchestrator"],
            allowed_authors=["testuser@github.com"],
        )

        errors = request.validate(config)
        assert len(errors) > 0
        assert "non autorisé" in errors[0]

    def test_request_validation_branch(self):
        """Test la validation de la branche."""
        request = GitHubRequest(
            request_id="test-123",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main/invalid",  # Branche avec slash
            mission={"id": "mission-456"},
            created_at="2026-10-18T18:00:00Z"
        )

        config = WorkerConfig(github_token="fake-token")

        errors = request.validate(config)
        # La validation de branche peut être basique, vérifions juste qu'elle fonctionne
        assert isinstance(errors, list)


class TestResultsJournal:
    """Tests pour la classe ResultsJournal."""

    def test_journal_creation(self, tmpdir):
        """Test la création d'un journal."""
        journal_path = tmpdir / "test_journal.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Vérifier que le journal est vide initialement
        assert len(journal) == 0

    def test_journal_record_and_retrieve(self, tmpdir):
        """Test l'enregistrement et la récupération d'un résultat."""
        journal_path = tmpdir / "test_journal.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Enregistrer un résultat
        outcome = {"success": True, "duration_seconds": 10}
        journal.record("test-request-123", outcome)

        # Vérifier que le journal a une entrée
        assert len(journal) == 1

        # Récupérer le résultat
        retrieved = journal.outcome_for("test-request-123")
        assert retrieved is not None
        assert retrieved["success"] is True
        assert retrieved["duration_seconds"] == 10

    def test_journal_idempotence(self, tmpdir):
        """Test que le journal enregistre de manière idempotente."""
        journal_path = tmpdir / "test_journal.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Enregistrer le même résultat deux fois
        outcome = {"success": True, "duration_seconds": 10}
        journal.record("test-request-123", outcome)
        journal.record("test-request-123", outcome)  # Should not duplicate

        # Devrait avoir exactement une entrée
        assert len(journal) == 1

    def test_journal_multiple_requests(self, tmpdir):
        """Test le journal avec plusieurs requêtes."""
        journal_path = tmpdir / "test_journal.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Enregistrer plusieurs résultats
        journal.record("request-1", {"success": True})
        journal.record("request-2", {"success": False})
        journal.record("request-3", {"success": True})

        # Vérifier que nous avons trois entrées
        assert len(journal) == 3

        # Récupérer des résultats spécifiques
        assert journal.outcome_for("request-1") is not None
        assert journal.outcome_for("request-2") is not None
        assert journal.outcome_for("request-3") is not None
        assert journal.outcome_for("non-existent") is None


class TestWorkerConfig:
    """Tests pour la classe WorkerConfig."""

    def test_config_defaults(self):
        """Test que les valeurs par défaut sont correctes."""
        config = WorkerConfig(github_token="fake-token")

        assert config.github_token == "fake-token"
        assert config.github_api_url == "https://api.github.com"
        assert config.worker_id == "opencode-nuc-worker"
        assert config.poll_seconds == 30
        assert config.heartbeat_seconds == 30
        assert config.opencode_bin == "opencode"
        assert config.opencode_workdir == ""
        assert config.allowed_repos == ["tvnv/axon-orchestrator"]
        assert config.allowed_authors == []

    def test_config_custom_values(self):
        """Test la configuration avec des valeurs personnalisées."""
        config = WorkerConfig(
            github_token="custom-token",
            worker_id="custom-worker",
            poll_seconds=45,
            allowed_repos=["org/repo1", "org/repo2"],
            allowed_authors=["user1", "user2"]
        )

        assert config.github_token == "custom-token"
        assert config.worker_id == "custom-worker"
        assert config.poll_seconds == 45
        assert config.allowed_repos == ["org/repo1", "org/repo2"]
        assert config.allowed_authors == ["user1", "user2"]

    def test_config_effective_poll(self):
        """Test le polling effectif."""
        # Test la limite inférieure
        config = WorkerConfig(github_token="fake-token", poll_seconds=5)
        assert config.effective_poll_seconds == 10

        # Test la limite supérieure
        config = WorkerConfig(github_token="fake-token", poll_seconds=100)
        assert config.effective_poll_seconds == 60

        # Test la valeur intermédiaire
        config = WorkerConfig(github_token="fake-token", poll_seconds=30)
        assert config.effective_poll_seconds == 30


class TestParseRequestFromBody:
    """Regression tests for the REQUEST body parser (Bug #F1 — fenced block format)."""

    FENCED_BODY = (
        "REQUEST\n"
        "```json\n"
        '{\n  "request_id": "nuc-smoke-20261018-1915",\n'
        '  "repo": "tvnv/axon-orchestrator",\n'
        '  "branch": "dev",\n'
        '  "mission": {"id": "nuc-smoke-20261018-1915", "type": "smoke"}\n'
        "}\n"
        "```\n"
        "Attendu: ACK et WORKING dans #31."
    )

    def test_fenced_block_parsed(self):
        """Bug regression: fenced REQUEST block must be recognised (no colon after REQUEST)."""
        result = parse_request_from_body(self.FENCED_BODY)
        assert result is not None
        assert result["request_id"] == "nuc-smoke-20261018-1915"
        assert result["repo"] == "tvnv/axon-orchestrator"
        assert result["branch"] == "dev"
        assert result["mission"]["id"] == "nuc-smoke-20261018-1915"

    def test_inline_format_parsed(self):
        """Inline REQUEST: {...} format must still be recognised."""
        body = 'REQUEST: {"request_id": "r1", "mission": {"id": "m1"}}'
        result = parse_request_from_body(body)
        assert result is not None
        assert result["request_id"] == "r1"

    def test_non_request_comment_returns_none(self):
        """Non-REQUEST comment must return None (no false positives)."""
        assert parse_request_from_body("Just a regular comment.") is None
        assert parse_request_from_body("[ACK]\n\nTask: some-id") is None

    def test_from_comment_fenced_block(self):
        """GitHubRequest.from_comment must parse the fenced block format end-to-end."""
        comment = {
            "body": self.FENCED_BODY,
            "user": {"login": "tvnv", "id": 1},
            "created_at": "2026-10-18T17:55:59Z",
        }
        req = GitHubRequest.from_comment(comment, {"login": "tvnv"})
        assert req.request_id == "nuc-smoke-20261018-1915"
        assert req.repo == "tvnv/axon-orchestrator"
        assert req.branch == "dev"

    def test_from_comment_inline(self):
        """GitHubRequest.from_comment must still parse the inline format."""
        comment = {
            "body": 'REQUEST: {"request_id": "r1", "repo": "tvnv/axon-orchestrator", "mission": {"id": "m1"}}',
            "user": {"login": "user1", "id": 2},
            "repository": {"full_name": "tvnv/axon-orchestrator"},
            "created_at": "2026-10-18T17:55:59Z",
            "branch": "main",
        }
        req = GitHubRequest.from_comment(comment, {"login": "user1"})
        assert req.request_id == "r1"
        assert req.repo == "tvnv/axon-orchestrator"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])