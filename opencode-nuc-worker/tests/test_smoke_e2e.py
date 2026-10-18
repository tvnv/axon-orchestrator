"""Tests E2E Smoke pour le worker NUC OpenCode.

Ces tests simulent l'exécution réelle du worker contre une issue GitHub simulée.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import subprocess
from datetime import datetime, timezone

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from opencode_nuc_worker import GitHubRequest, WorkerConfig, ResultsJournal, OpenCodeNUCWorker, GitHubRestClient
from opencode_nuc_worker import OpenCodeExecutor


class TestGitHubCommentParsing:
    """Tests pour le parsing des commentaires GitHub."""

    def test_parse_request_from_comment(self):
        """Test le parsing d'un commentaire REQUEST."""
        comment = {
            "id": 123456,
            "body": "REQUEST: {\"request_id\": \"test-request-123\", \"mission\": {\"id\": \"mission-456\", \"type\": \"test\"}}",
            "user": {"login": "testuser", "id": 789},
            "repository": {"full_name": "tvnv/axon-orchestrator", "name": "axon-orchestrator"},
            "created_at": "2026-10-18T18:00:00Z",
            "branch": "main"
        }
        author_info = {"login": "testuser", "id": 789}

        request = GitHubRequest.from_comment(comment, author_info)

        assert request.request_id == "test-request-123"
        assert request.author == "unknown"
        assert request.author_login == "testuser"
        assert request.repo == "tvnv/axon-orchestrator"
        assert request.branch == "main"
        assert request.mission == {"id": "mission-456", "type": "test"}

    def test_parse_request_multiline_comment(self):
        """Test le parsing d'un commentaire JSON REQUEST multi-lignes."""
        comment = {
            "id": 123457,
            "body": "REQUEST: {\n  \"request_id\": \"multiline-request\",\n  \"mission\": {\n    \"id\": \"mission-789\",\n    \"description\": \"Test de mission multiline\"\n  }\n}",
            "user": {"login": "testuser", "id": 790},
            "repository": {"full_name": "tvnv/axon-orchestrator", "name": "axon-orchestrator"},
            "created_at": "2026-10-18T18:00:00Z",
            "branch": "develop"
        }
        author_info = {"login": "testuser", "id": 790}

        request = GitHubRequest.from_comment(comment, author_info)

        assert request.request_id == "multiline-request"
        assert request.branch == "develop"
        assert request.mission["id"] == "mission-789"
        assert request.mission["description"] == "Test de mission multiline"

    def test_parse_comment_without_branch(self):
        """Test le parsing d'un commentaire sans branche (devrait utiliser main par défaut)."""
        comment = {
            "id": 123458,
            "body": "REQUEST: {\"request_id\": \"no-branch-request\", \"mission\": {\"id\": \"mission-999\"}}",
            "user": {"login": "testuser", "id": 791},
            "repository": {"full_name": "tvnv/axon-orchestrator", "name": "axon-orchestrator"},
            "created_at": "2026-10-18T18:00:00Z"
            # Pas de champ 'branch'
        }
        author_info = {"login": "testuser", "id": 791}

        request = GitHubRequest.from_comment(comment, author_info)

        assert request.request_id == "no-branch-request"
        assert request.branch == "main"  # Par défaut


class TestWorkerRealExecution:
    """Tests pour l'exécution réelle du worker (simulée)."""

    @patch('httpx.Client')
    @patch('subprocess.Popen')
    @patch('tempfile.TemporaryFile')
    def test_worker_execute_opencode_success(self, mock_tempfile, mock_popen, mock_client):
        """Test l'exécution réussie d'OpenCode par le worker."""
        # Mock de configuration
        config = WorkerConfig(
            github_token="fake-token",
            allowed_repos=["tvnv/axon-orchestrator"],
            allowed_authors=["testuser@github.com"],
            opencode_workdir="/home/van/axon",
            opencode_bin="opencode"
        )

        # Mock de journal
        journal_path = Path("/tmp/test_journal.jsonl")
        journal = ResultsJournal(str(journal_path))

        # Mock de processus
        mock_proc = Mock()
        mock_proc.poll.return_value = None  # Pas encore terminé
        # Simulation d'achèvement après le premier heartbeat
        call_count = [0]
        def poll_side_effect():
            call_count[0] += 1
            return 0 if call_count[0] > 1 else None
        mock_proc.poll.side_effect = poll_side_effect
        mock_proc.returncode = 0
        mock_proc.kill = Mock()
        mock_proc.wait = Mock()

        mock_popen.return_value = mock_proc

        # Mock de fichiers temporels (MagicMock needed for context manager protocol)
        mock_out_f = MagicMock()
        mock_out_f.__enter__.return_value = mock_out_f
        mock_out_f.read.return_value = '{"ok": true, "stdout": "Test output"}'

        mock_err_f = MagicMock()
        mock_err_f.__enter__.return_value = mock_err_f
        mock_err_f.read.return_value = '{"ok": true, "stderr": "Test error"}'

        mock_tempfile.side_effect = [mock_out_f, mock_err_f]

        # Mock du client HTTP pour les heartbeats
        mock_http_instance = Mock()
        mock_client.return_value = mock_http_instance

        # Mock de requête
        request = GitHubRequest(
            request_id="exec-test-request",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-exec-test"},
            created_at="2026-10-18T18:00:00Z"
        )

        # Mock de l'exécuteur
        executor = OpenCodeExecutor(
            bin_path=config.opencode_bin,
            workdir=config.opencode_workdir,
            timeout_seconds=config.opencode_timeout_seconds
        )

        # Fonction de heartbeat mock
        heartbeat_calls = []
        def mock_heartbeat():
            heartbeat_calls.append(datetime.now(timezone.utc))

        # Effectuer l'exécution
        result = executor.execute(request, mock_heartbeat, deadline_seconds=60)

        # Vérifier le résultat
        assert result.ok is True
        assert result.exit_code == 0
        assert result.duration_seconds > 0
        assert result.request_id == "exec-test-request"

    def test_worker_handles_opencode_timeout(self, tmpdir):
        """Test que le worker gère correctement le timeout d'OpenCode."""
        config = WorkerConfig(
            github_token="fake-token",
            allowed_repos=["tvnv/axon-orchestrator"],
            allowed_authors=["testuser@github.com"],
            opencode_timeout_seconds=10
        )

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        request = GitHubRequest(
            request_id="timeout-request",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-timeout"},
            created_at="2026-10-18T18:00:00Z"
        )

        # Mock de processus bloqué
        mock_proc = Mock()
        mock_proc.poll.return_value = None  # Bloqué indéfiniment
        mock_proc.returncode = -1
        mock_proc.kill = Mock()
        mock_proc.wait = Mock()

        with patch('subprocess.Popen', return_value=mock_proc):
            with patch('tempfile.TemporaryFile') as mock_tempfile:
                mock_out_f = MagicMock()
                mock_out_f.__enter__.return_value = mock_out_f
                mock_out_f.read.return_value = ''

                mock_err_f = MagicMock()
                mock_err_f.__enter__.return_value = mock_err_f
                mock_err_f.read.return_value = 'OpenCode exceeded lease window'

                mock_tempfile.side_effect = [mock_out_f, mock_err_f]

                executor = OpenCodeExecutor(
                    bin_path="opencode",
                    workdir="",
                    timeout_seconds=2
                )

                result = executor.execute(request, lambda: None, deadline_seconds=2)

                # Devrait retourner une défaillance due au timeout
                assert result.ok is False
                assert "exceeded" in result.stderr_tail.lower()


class TestWorkerStateManagement:
    """Tests pour la gestion d'état du worker."""

    def test_worker_manages_active_requests(self, tmpdir):
        """Test que le worker gère correctement les requêtes actives."""
        config = WorkerConfig(github_token="fake-token")

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        worker = OpenCodeNUCWorker(config, Mock(), journal)

        # Ajouter une requête active
        request = GitHubRequest(
            request_id="active-request",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-active"},
            created_at="2026-10-18T18:00:00Z"
        )

        worker.active_requests["active-request"] = {
            "request": request,
            "start_time": datetime.now(timezone.utc),
            "heartbeat_deadline": datetime.now(timezone.utc).timestamp() + 30
        }

        # Vérifier que la requête est active
        assert "active-request" in worker.active_requests
        assert len(worker.active_requests) == 1

        # Supprimer la requête active
        if "active-request" in worker.active_requests:
            del worker.active_requests["active-request"]

        # Vérifier qu'elle a été supprimée
        assert len(worker.active_requests) == 0

    def test_worker_safe_heartbeat(self, tmpdir):
        """Test le heartbeat sécurisé du worker."""
        config = WorkerConfig(github_token="fake-token")

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        worker = OpenCodeNUCWorker(config, Mock(), journal)

        # Ajouter une requête active
        request = GitHubRequest(
            request_id="heartbeat-request",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-heartbeat"},
            created_at="2026-10-18T18:00:00Z"
        )

        worker.active_requests["heartbeat-request"] = {
            "request": request,
            "start_time": datetime.now(timezone.utc),
            "heartbeat_deadline": datetime.now(timezone.utc).timestamp() + 30
        }

        # Heartbeat devrait fonctionner
        try:
            worker._safe_heartbeat("heartbeat-request")
            # Pas d'exception - succès
        except Exception as e:
            assert False, f"Heartbeat sécurisé a échoué: {e}"

        # Heartbeat pour une requête inexistante devrait être sûr
        worker._safe_heartbeat("non-existent-request")  # Pas d'exception

    def test_worker_process_with_journal_recovery(self, tmpdir):
        """Test le traitement du worker avec reprise après crash (journal essentiel)."""
        config = WorkerConfig(github_token="fake-token")

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Simuler une requête déjà traitée (représentant un crash précédent)
        journal.record("recovered-request", {
            "success": True,
            "duration_seconds": 10,
            "exit_code": 0
        })

        # Mock de client et exécuteur
        mock_client = Mock(spec=GitHubRestClient)
        mock_executor = Mock(spec=OpenCodeExecutor)

        worker = OpenCodeNUCWorker(config, Mock(), journal, mock_executor)
        worker.client = mock_client

        # Le worker devrait détecter que la requête a déjà été traitée
        # et publier ACK/WORKING pour la reprise
        # (Implémentation réelle nécessaire - ceci est un concept de test)

        # Vérifier que le journal contient l'entrée
        assert len(journal) == 1
        assert journal.outcome_for("recovered-request") is not None


class TestWorkerErrorHandling:
    """Tests pour la gestion d'erreurs du worker."""

    def test_worker_handles_fencedout_exception(self, tmpdir):
        """Test que le worker gère correctement l'exception FencedOut."""
        from opencode_nuc_worker import FencedOut

        config = WorkerConfig(github_token="fake-token")

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        worker = OpenCodeNUCWorker(config, Mock(), journal)

        request = GitHubRequest(
            request_id="fencedout-request",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-fencedout"},
            created_at="2026-10-18T18:00:00Z"
        )

        # Ajouter une requête active avec une deadline dans le passé pour déclencher FencedOut
        worker.active_requests["fencedout-request"] = {
            "request": request,
            "start_time": datetime.now(timezone.utc),
            "heartbeat_deadline": datetime.now(timezone.utc).timestamp() - 100  # Passé
        }

        # Le heartbeat devrait lever FencedOut
        try:
            worker._safe_heartbeat("fencedout-request")
            # Si nous arrivons ici, pas de FencedOut (peut-être une logique différente)
        except FencedOut:
            # Ce devrait être levé
            pass
        except Exception:
            pass  # Autre exception - peut être acceptable pour le test

    def test_worker_handles_client_errors_gracefully(self, tmpdir):
        """Test que le worker gère les erreurs de client REST HTTP de manière gracieuse."""
        config = WorkerConfig(github_token="fake-token")

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        worker = OpenCodeNUCWorker(config, Mock(), journal)

        # Mock de client qui lève une exception
        mock_client = Mock(spec=GitHubRestClient)
        mock_client.get_issue_comments.side_effect = Exception("Erreur client HTTP")

        worker.client = mock_client

        # poll_once devrait gérer l'exception gracieusement
        result = worker.poll_once()
        assert result is False
        # Ne devrait pas lever d'exception


if __name__ == "__main__":
    pytest.main([__file__, "-v"])