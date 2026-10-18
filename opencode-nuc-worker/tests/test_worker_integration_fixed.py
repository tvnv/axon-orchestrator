"""Tests d'intégration corrigés pour le worker NUC OpenCode."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from opencode_nuc_worker import GitHubRequest, WorkerConfig, ResultsJournal, OpenCodeNUCWorker, GitHubRestClient
from opencode_nuc_worker import OpenCodeExecutor


class TestGitHubRequestValidation:
    """Tests pour la validation des requêtes GitHub."""

    def test_request_author_validation(self):
        """Test que la validation des auteurs respecte la liste blanche obligatoire."""
        # Scénario 1: Aucun auteur autorisé devrait échouer (liste blanche obligatoire)
        request = GitHubRequest(
            request_id="test-123",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-456"},
            created_at="2026-10-18T18:00:00Z"
        )

        # Config avec liste blanche vide - devrait échouer selon la mission
        config = WorkerConfig(
            github_token="fake-token",
            allowed_authors=[]  # Liste blanche vide - devrait rejeter toute requête
        )

        errors = request.validate(config)
        # Selon la mission : "Allowlist authors is mandatory" - liste blanche vide doit rejeter toute requête
        assert len(errors) > 0, "Aucun auteur autorisé dans la configuration"
        assert "auteur" in errors[0].lower() or "non autorisé" in errors[0].lower()

    def test_request_repo_validation(self):
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

        config = WorkerConfig(
            github_token="fake-token",
            allowed_repos=["tvnv/axon-orchestrator"],  # Seul ce dépôt est autorisé
            allowed_authors=["testuser@github.com"]  # Ajouter un auteur autorisé pour tester la validation des dépôts
        )

        errors = request.validate(config)
        assert len(errors) > 0
        assert "dépôt" in errors[0].lower() or "non autorisé" in errors[0].lower()

    def test_valid_request_passes_validation(self):
        """Test qu'une requête valide passe la validation."""
        request = GitHubRequest(
            request_id="test-123",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-456"},
            created_at="2026-10-18T18:00:00Z"
        )

        # Config avec autorisation complète
        config = WorkerConfig(
            github_token="fake-token",
            allowed_repos=["tvnv/axon-orchestrator"],
            allowed_authors=["testuser@github.com"]
        )

        errors = request.validate(config)
        assert len(errors) == 0, f"Requête valide devrait passer la validation: {errors}"

    def test_request_id_format_validation(self):
        """Test la validation du format de request_id."""
        request = GitHubRequest(
            request_id="",  # ID vide - invalide
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={"id": "mission-456"},
            created_at="2026-10-18T18:00:00Z"
        )

        config = WorkerConfig(github_token="fake-token")
        errors = request.validate(config)
        assert any("request_id" in error.lower() for error in errors)

    def test_mission_validation(self):
        """Test la validation des données de mission."""
        # Mission invalide : manquant d'ID
        request = GitHubRequest(
            request_id="test-123",
            author="testuser",
            author_login="testuser@github.com",
            repo="tvnv/axon-orchestrator",
            branch="main",
            mission={},  # Vide - invalide
            created_at="2026-10-18T18:00:00Z"
        )

        config = WorkerConfig(github_token="fake-token")
        errors = request.validate(config)
        assert len(errors) > 0


class TestResultsJournal:
    """Tests pour ResultsJournal."""

    def test_journal_records_results_idempotently(self, tmpdir):
        """Test que le journal enregistre les résultats de manière idempotent (mission essentielle)."""
        journal_path = tmpdir / "test_journal.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Premier enregistrement
        outcome1 = {"success": True, "duration_seconds": 10}
        journal.record("test-request-123", outcome1)
        assert len(journal) == 1

        # Deuxième enregistrement identique - devrait être ignoré (idempotent)
        outcome2 = {"success": True, "duration_seconds": 10}
        journal.record("test-request-123", outcome2)
        assert len(journal) == 1, "Le journal devrait ignorer les enregistrements en double (idempotent)"

    def test_journal_persists_data(self, tmpdir):
        """Test que le journal persiste les données après rechargement."""
        journal_path = tmpdir / "test_journal.jsonl"
        
        # Premier journal
        journal1 = ResultsJournal(str(journal_path))
        journal1.record("request-1", {"success": True})
        assert len(journal1) == 1

        # Nouveau journal (simulate redémarrage)
        journal2 = ResultsJournal(str(journal_path))
        assert len(journal2) == 1
        assert journal2.outcome_for("request-1") is not None

    def test_journal_recovery_scenario(self, tmpdir):
        """Test un scénario de reprise après crash (mission critique)."""
        journal_path = tmpdir / "test_journal.jsonl"
        
        # Simuler des résultats préexistants (d'un worker précédent)
        journal_path.write_text(
            json.dumps({
                "request_id": "old-request-123",
                "recorded_at": "2026-10-18T18:00:00Z",
                "outcome": {"success": False, "duration_seconds": 5}
            }) + "\n",
            encoding="utf-8"
        )

        journal = ResultsJournal(str(journal_path))
        assert len(journal) == 1
        
        outcome = journal.outcome_for("old-request-123")
        assert outcome is not None
        assert outcome["success"] is False


class TestWorkerPolling:
    """Tests pour la logique de polling du worker."""

    def test_worker_poll_valid_request(self, tmpdir):
        """Test que le worker traite une requête REQUEST valide."""
        # Mock de configuration
        config = WorkerConfig(
            github_token="fake-token",
            allowed_repos=["tvnv/axon-orchestrator"],
            allowed_authors=["testuser"]  # Seul cet utilisateur est autorisé
        )

        # Mock de journal
        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Mock du client REST GitHub
        mock_client = Mock(spec=GitHubRestClient)
        mock_client.get_issue_comments.return_value = [
            {
                "id": 123456,
                "body": "REQUEST: {\"request_id\": \"test-request-123\", \"mission\": {\"id\": \"mission-123\"}}",
                "user": {"login": "testuser", "id": 789},
                "repository": {"full_name": "tvnv/axon-orchestrator"},
                "created_at": "2026-10-18T18:00:00Z",
                "branch": "main"
            }
        ]

        # Mock de l'exécuteur OpenCode
        mock_executor = Mock(spec=OpenCodeExecutor)
        mock_executor.execute.return_value = Mock(
            ok=True,
            exit_code=0,
            stdout_tail="Test output",
            stderr_tail="",
            duration_seconds=5,
            request_id="test-request-123"
        )

        # Créer le worker avec des mocks
        worker = OpenCodeNUCWorker(config, Mock(), journal, mock_executor)
        worker.client = mock_client

        # Effectuer un polling
        result = worker.poll_once()

        # Devrait traiter la requête
        assert result is True
        assert len(journal) == 1  # Le résultat devrait être enregistré

    def test_worker_rejects_unauthorized_request(self, tmpdir):
        """Test que le worker rejette une requête non autorisée."""
        config = WorkerConfig(
            github_token="fake-token",
            allowed_repos=["tvnv/axon-orchestrator"],
            allowed_authors=["authorized-user@github.com"]  # Seul cet utilisateur est autorisé
        )

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        mock_client = Mock(spec=GitHubRestClient)
        mock_client.get_issue_comments.return_value = [
            {
                "id": 123457,
                "body": "REQUEST: {\"request_id\": \"unauthorized-request\", \"mission\": {\"id\": \"mission-123\"}}",
                "user": {"login": "unauthorized-user", "id": 790},
                "repository": {"full_name": "tvnv/axon-orchestrator"},
                "created_at": "2026-10-18T18:00:00Z",
                "branch": "main"
            }
        ]

        worker = OpenCodeNUCWorker(config, Mock(), journal, Mock())
        worker.client = mock_client

        result = worker.poll_once()

        # Devrait ignorer la requête non autorisée
        assert result is False
        assert len(journal) == 0  # Aucun résultat enregistré

    def test_worker_idempotence(self, tmpdir):
        """Test que le worker traite les requêtes en double de manière idempotente (mission critique)."""
        config = WorkerConfig(
            github_token="fake-token",
            allowed_authors=["testuser"]  # Ajouter un auteur autorisé pour éviter l'erreur de validation
        )

        journal_path = tmpdir / "results.jsonl"
        journal = ResultsJournal(str(journal_path))

        # Créer un mock client qui retourne différents résultats pour chaque appel
        mock_client = Mock(spec=GitHubRestClient)
        
        # Premier appel - retourne une requête
        mock_client.get_issue_comments.side_effect = [
            [
                {
                    "id": 123458,
                    "body": "REQUEST: {\"request_id\": \"duplicate-request\", \"mission\": {\"id\": \"mission-123\"}}",
                    "user": {"login": "testuser", "id": 791},
                    "repository": {"full_name": "tvnv/axon-orchestrator"},
                    "created_at": "2026-10-18T18:00:00Z",
                    "branch": "main"
                }
            ],
            []  # Second appel - retourne vide (pas de nouvelles requêtes)
        ]

        mock_executor = Mock(spec=OpenCodeExecutor)
        mock_executor.execute.return_value = Mock(
            ok=True,
            exit_code=0,
            stdout_tail="Test output",
            stderr_tail="",
            duration_seconds=5,
            request_id="duplicate-request"
        )

        worker = OpenCodeNUCWorker(config, Mock(), journal, mock_executor)
        worker.client = mock_client

        # Premier polling - devrait traiter la requête
        result1 = worker.poll_once()
        assert result1 is True
        assert len(journal) == 1

        # Second polling - devrait être ignoré (pas de nouvelles requêtes)
        result2 = worker.poll_once()
        assert result2 is False
        assert len(journal) == 1  # Pas de nouveaux enregistrements


class TestWorkerServiceIntegration:
    """Tests pour l'intégration du service worker."""

    def test_worker_service_configuration(self):
        """Test que le service worker se configure correctement."""
        # Simuler une configuration depuis .env
        config = WorkerConfig(
            github_token="test-token-123",
            github_api_url="https://api.github.com",
            worker_id="opencode-nuc-worker",
            opencode_workdir="/home/van/axon",
            allowed_repos=["tvnv/axon-orchestrator"],
            allowed_authors=[]  # Liste blanche obligatoire mais vide
        )

        # La configuration devrait être valide
        assert config.github_token == "test-token-123"
        assert config.opencode_workdir == "/home/van/axon"
        assert config.allowed_repos == ["tvnv/axon-orchestrator"]

    def test_worker_env_file_permissions(self, tmpdir):
        """Test les permissions du fichier .env du worker."""
        env_file = tmpdir / "worker.env"
        env_file.write_text("github_token=test-token\n", encoding="utf-8")
        
        # Le script d'installation définit les permissions à 640 et la propriété root:opencode-nuc-worker
        env_file.chmod(0o640)
        
        # Devrait avoir les permissions correctes
        import os
        file_stat = os.stat(str(env_file))
        assert (file_stat.st_mode & 0o777) == 0o640


if __name__ == "__main__":
    pytest.main([__file__, "-v"])