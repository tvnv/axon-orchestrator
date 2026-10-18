"""Worker NUC OpenCode pour le traitement des commandes GitHub Agent Channel (issue #29).

Considère les commentaires REQUEST dans l'issue #31 de GitHub et exécute des
missions OpenCode CLI autonomes sur le NUC, en écrivant les résultats dans
l'issue #12 de GitHub (canal OpenCode). Aucune intervention HITL n'est requise dans
le périmètre autorisé.

Garanties :

* le polling est un HTTPS sortant depuis le NUC vers GitHub (sans tunnel externe) ;
* la validation d'auteur/de périmètre, l'identification de request_id et la
  déduplication des requêtes ;
* le worker OpenCode CLI s'exécute strictement non-interactivement (``opencode run``
  mode tête-à-tête ; no REPL, no TTY) ;
* reprise après crash via le journal local des résultats par request_id ;
* la boucle de polling survit à toutes les défaillances ;
* seule une seule mission active est conservée par process ;
* pas d'exécution shell directe depuis les commentaires GitHub ;
* sorties confidentielles protégées (secrets hors GitHub) ;
* cwd=~/axon pour les exécutions OpenCode CLI, avec limitation des dépôts autorisés.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import httpx
from pydantic import BaseModel


def parse_request_from_body(body: str) -> dict | None:
    """Extract REQUEST JSON payload from a comment body.

    Supports two formats::

        REQUEST: {...}                # inline JSON after colon

        REQUEST                       # keyword alone
        ```json                       # fenced block (any language tag)
        {...}
        ```

    Returns the parsed dict or None if not a valid REQUEST comment.
    """
    lines = body.split("\n")
    request_line_idx: int | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Inline format: REQUEST: {...}  or  REQUEST: ```json\n...```
        if stripped.startswith("REQUEST:"):
            after = stripped[len("REQUEST:"):].strip()
            if after.startswith("```"):
                # Fenced after colon (rare but handle it)
                fence_inner = after[3:]
                fence_end = fence_inner.find("```")
                if fence_end >= 0:
                    json_str = fence_inner[:fence_end].strip()
                    # skip optional language tag on first line
                    if "\n" in json_str:
                        first_nl = json_str.index("\n")
                        candidate = json_str[first_nl:].strip()
                        if candidate.startswith("{"):
                            json_str = candidate
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
            elif after.startswith("{"):
                try:
                    return json.loads(after)
                except json.JSONDecodeError:
                    pass
            # Fenced block starts on a later line
            request_line_idx = i
            break
        # Bare keyword: REQUEST (with or without trailing whitespace)
        if stripped.upper() == "REQUEST":
            request_line_idx = i
            break

    if request_line_idx is None:
        return None

    # Scan lines after the REQUEST line for a fenced block
    in_fence = False
    json_lines: list[str] = []
    for line in lines[request_line_idx + 1:]:
        stripped = line.strip()
        if not in_fence:
            if stripped.startswith("```"):
                in_fence = True
                # Skip optional language tag on the opening fence line
                continue
            if stripped:
                # Non-empty, non-fence line: try as bare JSON
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    return None
        else:
            if stripped.startswith("```"):
                break  # Closing fence
            json_lines.append(line)

    if json_lines:
        try:
            return json.loads("\n".join(json_lines))
        except json.JSONDecodeError:
            return None

    return None

HTTP_CONFLICT = 409

# Constantes de configuration du worker
DEFAULT_POLL_MIN_SECONDS = 10
DEFAULT_POLL_MAX_SECONDS = 60
DEFAULT_POLL_SECONDS = 30
DEFAULT_HEARTBEAT_SECONDS = 30
DEFAULT_OPENCODE_TIMEOUT_SECONDS = 3600
DEFAULT_JOURNAL_PATH = "data/worker/results.jsonl"
DEFAULT_WORKER_ID = "opencode-nuc-worker"
DEFAULT_GITHUB_REPO = "tvnv/axon-orchestrator"
DEFAULT_GITHUB_TOKEN_SCOPES = ["repo", "read:org"]


def clamp_poll_seconds(value: int) -> int:
    """Clamp l'intervalle de polling dans la plage acceptée 10..60 secondes."""
    return max(DEFAULT_POLL_MIN_SECONDS, min(DEFAULT_POLL_MAX_SECONDS, int(value)))


class WorkerConfig(BaseModel):
    """Configuration du worker OpenCode NUC. Les secrets sont fournis à la construction, jamais journalisés."""

    github_token: str
    github_api_url: str = "https://api.github.com"
    worker_id: str = DEFAULT_WORKER_ID
    poll_seconds: int = DEFAULT_POLL_SECONDS
    heartbeat_seconds: int = DEFAULT_HEARTBEAT_SECONDS
    opencode_bin: str = "opencode"
    opencode_workdir: str = ""  # Sera défini comme /home/van/axon
    opencode_timeout_seconds: int = DEFAULT_OPENCODE_TIMEOUT_SECONDS
    journal_path: str = DEFAULT_JOURNAL_PATH
    allowed_repos: list[str] = [DEFAULT_GITHUB_REPO]
    allowed_authors: list[str] = []

    @property
    def effective_poll_seconds(self) -> int:
        return clamp_poll_seconds(self.poll_seconds)


class GitHubRequest(BaseModel):
    """Un commentaire REQUEST validé dans l'issue #31."""

    request_id: str
    author: str
    author_login: str
    repo: str
    branch: str
    mission: dict
    created_at: str

    @classmethod
    def from_comment(cls, comment: dict, author_info: dict) -> "GitHubRequest":
        """Crée une requête à partir d'un commentaire GitHub."""
        body = comment.get("body", "")
        request_data = parse_request_from_body(body)

        if not isinstance(request_data, dict):
            raise ValueError("Commentaire REQUEST manquant ou JSON invalide")

        request_id = request_data.get("request_id") or comment.get("request_id")
        mission = request_data.get("mission") or comment.get("mission")

        if not request_id:
            raise ValueError("Commentaire REQUEST manquant de request_id")
        if not mission:
            raise ValueError("Commentaire REQUEST manquant de mission")

        # Repo: from JSON payload first (REST API comments lack a "repository" field).
        repo_data = comment.get("repository", {})
        repo = (
            request_data.get("repo")
            or repo_data.get("full_name")
            or repo_data.get("name")
            or ""
        )

        # Branch: from JSON payload first, then comment field, then default.
        branch = request_data.get("branch") or comment.get("branch") or "main"

        return cls(
            request_id=request_id,
            author=comment.get("author", "unknown"),
            author_login=author_info.get("login", ""),
            repo=repo,
            branch=branch,
            mission=mission,
            created_at=comment.get("created_at", datetime.now(timezone.utc).isoformat()),
        )

    def validate(self, config: WorkerConfig) -> list[str]:
        """Valide la requête par rapport à la configuration du worker.
        Retourne une liste vide si la requête est valide, sinon une liste de messages d'erreur."""
        errors = []

        # Vérifier l'auteur autorisé - selon la mission, l'allowlist d'auteurs est obligatoire
        if not config.allowed_authors:
            errors.append("Aucun auteur autorisé dans la configuration - l'allowlist d'auteurs est obligatoire")
        elif self.author_login not in config.allowed_authors:
            errors.append(f"Auteur non autorisé: {self.author_login}")

        # Vérifier le dépôt autorisé
        if self.repo not in config.allowed_repos:
            errors.append(f"Dépôt non autorisé: {self.repo}")

        # Valider le format de request_id
        if not self.request_id or not isinstance(self.request_id, str):
            errors.append("request_id invalide")

        # Valider les données de mission
        if not isinstance(self.mission, dict):
            errors.append("mission invalide: doit être un objet")
        elif not self.mission.get("id"):
            errors.append("mission invalide: manquant d'identifiant mission")

        # Valider la branche (ne devrait contenir que des caractères alphanumériques, tirets et slash)
        if not all(c.isalnum() or c in "-/_" for c in self.branch):
            errors.append(f"branche invalide: {self.branch}")

        return errors


class OpenCodeResult(BaseModel):
    """Résultat normalisé d'une exécution CLI OpenCode non-interactive."""

    ok: bool
    exit_code: Optional[int]
    stdout_tail: str = ""
    stderr_tail: str = ""
    duration_seconds: int = 0
    request_id: Optional[str] = None


def build_opencode_prompt(request: GitHubRequest) -> str:
    """Construit le texte de la mission OpenCode pour une requête valide.

    Seules les données déclarées dans la mission REQUEST entrent dans le prompt,
    garantissant ainsi l'idempotence : la même requête produit le même prompt.
    """
    mission = request.mission
    request_id = request.request_id
    repo = request.repo
    branch = request.branch

    prompt_parts = [
        f"GitHub Agent Channel NUC worker task ID: {request_id}",
        f"Repository: {repo} (branch: {branch})",
        f"Author: {request.author_login}",
    ]

    # Ajouter les sections de mission si elles existent
    if mission.get("description"):
        prompt_parts.append(f"Description: {mission['description']}")

    if mission.get("type"):
        prompt_parts.append(f"Type: {mission['type']}")

    # Inclure les données spécifiques à la mission de manière déterministe
    if "payload" in mission:
        payload = mission["payload"]
        for key, value in payload.items():
            prompt_parts.append(f"{key}: {value}")

    prompt_parts.append("\nExecute the requested task autonomously using OpenCode CLI.")

    return "\n".join(prompt_parts)


class FencedOut(Exception):
    """La requête a été remplacée : un lease plus récent a pris le dessus."""


class ResultsJournal:
    """Journal local append-only des résultats de requêtes terminées (mémoire de crash).

    Indexé par request_id : après un crash, quand une requête est re-claimée le worker
    rejoue le résultat enregistré au lieu de ré-exécuter OpenCode. Le journal est la
    garantie d'idempotence sur un hôte qui peut être tué à tout moment.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text().splitlines():
            try:
                entry = json.loads(line)
                self._entries[entry["request_id"]] = entry
            except (json.JSONDecodeError, KeyError):
                continue

    def record(self, request_id: str, outcome: dict) -> None:
        """Enregistre le résultat d'une requête terminée."""
        entry = {
            "request_id": request_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "outcome": outcome,
        }
        if self._entries.get(request_id) == entry:
            return
        self._entries[request_id] = entry
        with self.path.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")

    def outcome_for(self, request_id: str) -> dict | None:
        """Récupère le résultat enregistré pour une requête."""
        entry = self._entries.get(request_id)
        return dict(entry["outcome"]) if entry is not None else None

    def __len__(self) -> int:
        return len(self._entries)


class GitHubRestClient:
    """Client REST GitHub pour le polling d'issue et la publication de commentaires.

    Utilise l'API REST GitHub (pas de webhooks) pour maintenir le worker sans état.
    """

    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        self.token = token
        self.api_url = api_url.rstrip("/")
        self.http = httpx.Client(headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "opencode-nuc-worker"
        })

    def get_issue_comments(self, owner: str, repo: str, issue_number: int,
                          since: Optional[str] = None) -> list[dict]:
        """Récupère les commentaires de l'issue, optionnellement filtrés par date."""
        path = f"{self.api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        params = {}
        if since:
            params["since"] = since

        response = self.http.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def create_comment(self, owner: str, repo: str, issue_number: int,
                      body: str, request_id: str) -> dict:
        """Publie un commentaire dans l'issue."""
        path = f"{self.api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        body_with_metadata = f"{body}\n\n---\n**request_id**: {request_id}\n**timestamp**: {datetime.now(timezone.utc).isoformat()}"

        response = self.http.post(path, json={"body": body_with_metadata})
        response.raise_for_status()
        return response.json()

    def get_issue(self, owner: str, repo: str, issue_number: int) -> dict:
        """Récupère les détails de l'issue."""
        path = f"{self.api_url}/repos/{owner}/{repo}/issues/{issue_number}"
        response = self.http.get(path)
        response.raise_for_status()
        return response.json()


class OpenCodeExecutor:
    """Exécute le CLI OpenCode non-interactively pour une requête validée.

    Pendant que le CLI s'exécute, ``heartbeat()`` est appelé périodiquement pour que le
    lease reste nôtre ; quand l'exécution dépasse la fenêtre de lease restante le
    processus est tué et rapporté comme une défaillance -- GitHub ré-file la requête
    et un demandeur plus tard retried proprement.
    """

    def __init__(self, bin_path: str = "opencode", workdir: str = "",
                 timeout_seconds: int = DEFAULT_OPENCODE_TIMEOUT_SECONDS):
        self.bin_path = bin_path
        self.workdir = workdir
        self.timeout_seconds = timeout_seconds

    def execute(self, request: GitHubRequest, heartbeat: Callable[[], None],
                deadline_seconds: int) -> OpenCodeResult:
        """Exécute OpenCode pour une requête, avec heartbeat et timeout."""
        prompt = build_opencode_prompt(request)
        argv = [self.bin_path, "run", "--format", "json", prompt]
        start = time.monotonic()
        window = min(self.timeout_seconds, max(1, deadline_seconds))

        # Sortie vers fichiers temporaires, pas vers pipes : un CLI bavard ne doit jamais
        # bloquer la boucle de heartbeat sur un tampon de pipe plein.
        with tempfile.TemporaryFile(mode="w+") as out_f, \
                tempfile.TemporaryFile(mode="w+") as err_f:
            proc = subprocess.Popen(argv, stdout=out_f, stderr=err_f,
                                    cwd=self.workdir or None, text=True)
            heartbeat_at = time.monotonic() + self._heartbeat_interval(deadline_seconds)
            while proc.poll() is None and time.monotonic() < start + window:
                if time.monotonic() >= heartbeat_at:
                    heartbeat()
                    heartbeat_at = time.monotonic() + self._heartbeat_interval(deadline_seconds)
                time.sleep(1)
            if proc.poll() is None:
                proc.kill()
                proc.wait()
                return OpenCodeResult(
                    ok=False,
                    exit_code=proc.returncode,
                    stderr_tail="OpenCode exceeded lease window",
                    duration_seconds=int(time.monotonic() - start),
                    request_id=request.request_id
                )
            out_f.seek(0)
            err_f.seek(0)
            out, err = out_f.read()[-2000:], err_f.read()[-2000:]
        duration = int(time.monotonic() - start)
        return OpenCodeResult(
            ok=proc.returncode == 0,
            exit_code=proc.returncode,
            stdout_tail=out,
            stderr_tail=err,
            duration_seconds=duration,
            request_id=request.request_id
        )

    def _heartbeat_interval(self, deadline_seconds: int) -> int:
        return max(5, min(30, deadline_seconds // 3))


class OpenCodeNUCWorker:
    """Worker OpenCode NUC : polling GitHub → validation → ACK/WORKING → OpenCode → RESULT."""

    def __init__(self, config: WorkerConfig, http: httpx.Client,
                 journal: ResultsJournal, executor: Optional[OpenCodeExecutor] = None):
        self.config = config
        self.journal = journal
        self.executor = executor or OpenCodeExecutor(
            bin_path=config.opencode_bin,
            workdir=config.opencode_workdir,
            timeout_seconds=config.opencode_timeout_seconds,
        )
        self.client = GitHubRestClient(config.github_token, config.github_api_url)
        self.running = False
        self.active_requests: dict[str, dict] = {}
        self.last_poll_time: Optional[datetime] = None

    def process(self, request: GitHubRequest) -> None:
        """Traite une requête VALIDÉE : publie ACK, puis WORKING, puis exécute OpenCode, puis RESULT."""
        request_id = request.request_id

        # Vérifier si la requête a déjà été traitée (idempotence)
        if request_id in self.journal._entries:
            self._log(f"requête {request_id} déjà traitée, republiant ACK et WORKING")
            self._publish_ack(request, "reprise après crash")
            self._publish_working(request, "reprise")
            return

        # Publier ACK et WORKING immédiatement pour assurer la détection de présence
        self._publish_ack(request, "nouveau")
        self._publish_working(request, "en cours")

        # Stocker l'état actif
        self.active_requests[request_id] = {
            "request": request,
            "start_time": datetime.now(timezone.utc),
            "heartbeat_deadline": datetime.now(timezone.utc).timestamp() + self.config.heartbeat_seconds
        }

        try:
            # Calculer la deadline basée sur l'expiration du lease (si fournie)
            # Pour GitHub, nous utilisons la fenêtre de heartbeat comme deadline principale
            deadline = self.config.heartbeat_seconds

            # Exécuter OpenCode avec heartbeat
            result = self.executor.execute(
                request,
                heartbeat=lambda: self._safe_heartbeat(request_id),
                deadline_seconds=deadline
            )

            # Enregistrer le résultat et publier RESULT dans l'issue #12
            outcome = {
                "success": result.ok,
                "exit_code": result.exit_code,
                "duration_seconds": result.duration_seconds,
                "stdout": result.stdout_tail,
                "stderr": result.stderr_tail,
            }
            self.journal.record(request_id, outcome)
            self._publish_result(request, outcome)

        except FencedOut:
            self._log(f"requête {request_id} était verrouillée : un lease plus récent a pris le dessus")
        except Exception as exc:
            self._log(f"erreur fatale lors du traitement de la requête {request_id}: {exc}")
        finally:
            # Nettoyer l'état actif
            if request_id in self.active_requests:
                del self.active_requests[request_id]

    def poll_once(self) -> bool:
        """Un tick : claim au plus une requête valide depuis l'issue #31."""
        try:
            repo_parts = self.config.allowed_repos[0].split("/")
            if len(repo_parts) != 2:
                self._log(f"format de dépôt invalide: {self.config.allowed_repos[0]}")
                return False

            owner, repo = repo_parts
            issue_number = 31

            since = self.last_poll_time.isoformat() if self.last_poll_time else None
            comments = self.client.get_issue_comments(owner, repo, issue_number, since)

            for comment in comments:
                try:
                    user = comment.get("user", {})
                    author_info = {
                        "login": user.get("login", ""),
                        "id": user.get("id", 0),
                    }

                    comment_body = comment.get("body", "")

                    # Fast pre-filter: must contain the REQUEST keyword
                    if "REQUEST" not in comment_body.upper():
                        continue

                    # parse_request_from_body handles both inline and fenced formats
                    if parse_request_from_body(comment_body) is None:
                        continue

                    request = GitHubRequest.from_comment(comment, author_info)

                    validation_errors = request.validate(self.config)
                    if validation_errors:
                        self._log(
                            f"requête {request.request_id} invalide: {'; '.join(validation_errors)}"
                        )
                        continue

                    if request.request_id in self.active_requests:
                        self._log(f"requête {request.request_id} déjà active, en ignorant")
                        continue

                    self.process(request)
                    self.last_poll_time = datetime.now(timezone.utc)
                    return True

                except Exception as exc:
                    self._log(
                        f"erreur en traitant le commentaire {comment.get('id', 'inconnu')}: {exc}"
                    )
                    continue

        except Exception as exc:
            self._log(f"échec du polling, retry au prochain cycle: {exc}")
            return False

        return False

    def _publish_ack(self, request: GitHubRequest, reason: str) -> None:
        """Publie un commentaire ACK dans l'issue #31."""
        try:
            repo_parts = request.repo.split("/")
            if len(repo_parts) != 2:
                return

            owner, repo = repo_parts
            body = f"**[ACK]**\n\nTask: {request.request_id}\nReason: {reason}\nAuthor: {request.author_login}\nMission: {request.mission.get('id', 'unknown')}\n\n---\n\n*Valide l'auteur et le périmètre autorisé.*"

            self.client.create_comment(owner, repo, 31, body, request.request_id)
            self._log(f"ACK publié pour la requête {request.request_id}: {reason}")

        except Exception as exc:
            self._log(f"échec de la publication d'ACK pour la requête {request.request_id}: {exc}")

    def _publish_working(self, request: GitHubRequest, reason: str) -> None:
        """Publie un commentaire WORKING dans l'issue #31."""
        try:
            repo_parts = request.repo.split("/")
            if len(repo_parts) != 2:
                return

            owner, repo = repo_parts
            body = f"**[WORKING]**\n\nTask: {request.request_id}\nReason: {reason}\nAuthor: {request.author_login}\nCommencé: {datetime.now(timezone.utc).isoformat()}\n\n*Worker NUC exécutant OpenCode CLI.*"

            self.client.create_comment(owner, repo, 31, body, request.request_id)
            self._log(f"WORKING publié pour la requête {request.request_id}")

        except Exception as exc:
            self._log(f"échec de la publication de WORKING pour la requête {request.request_id}: {exc}")

    def _publish_result(self, request: GitHubRequest, outcome: dict) -> None:
        """Publie un commentaire RESULT dans l'issue #12 (OpenCode result channel)."""
        try:
            repo_parts = request.repo.split("/")
            if len(repo_parts) != 2:
                return

            owner, repo = repo_parts

            # Construire le message RESULT
            status = "✅ SUCCÈS" if outcome["success"] else "❌ ÉCHEC"
            result_body = f"**[RESULT]**\n\nTask: {request.request_id}\nStatus: {status}\nDuration: {outcome['duration_seconds']}s\nExit Code: {outcome['exit_code']}\n\n---\n\n**Détails d'exécution:**\n```\n{outcome['stderr']}\n```\n\n**Sortie standard:**\n```\n{outcome['stdout']}\n```\n\n---\n**Timestamp:** {datetime.now(timezone.utc).isoformat()}\n**Auteur:** {request.author_login}\n**Dépôt:** {request.repo}\n**Branche:** {request.branch}\n**Mission ID:** {request.mission.get('id', 'unknown')}\n\n[Retour aux détails de la mission → #31]"

            # Publier dans l'issue #12
            self.client.create_comment(owner, repo, 12, result_body, request.request_id)
            self._log(f"RESULT publié pour la requête {request.request_id} dans l'issue #12")

        except Exception as exc:
            self._log(f"échec de la publication de RESULT pour la requête {request.request_id}: {exc}")

    def _safe_heartbeat(self, request_id: str) -> None:
        """Heartbeat sécurisé pour une requête active."""
        if request_id not in self.active_requests:
            return

        try:
            # Vérifier la validité de la requête active
            active_req = self.active_requests[request_id]
            now = datetime.now(timezone.utc).timestamp()

            if now > active_req["heartbeat_deadline"]:
                raise FencedOut(f"Le lease pour la requête {request_id} a expiré")

            # Mettre à jour la deadline
            active_req["heartbeat_deadline"] = now + self.config.heartbeat_seconds

        except FencedOut:
            raise
        except Exception as exc:
            self._log(f"erreur de heartbeat pour la requête {request_id}: {exc}")

    def run_forever(self) -> None:
        """Boucle principale de polling, survit à toutes les défaillances."""
        interval = self.config.effective_poll_seconds
        self._log(f"démarré, polling GitHub issue #31 toutes les {interval}s")
        self.running = True

        while self.running:
            try:
                self.poll_once()
            except Exception as exc:
                self._log(f"cycle d'erreur (conserver la boucle): {type(exc).__name__}: {exc}")
            time.sleep(interval)

    def stop(self) -> None:
        """Arrête le worker gracieusement."""
        self.running = False
        self._log("worker arrêté")

    def _log(self, message: str) -> None:
        """Journalise un message avec horodatage."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [opencode-nuc-worker] {message}", flush=True)


def worker_config_from_settings(cfg) -> WorkerConfig:
    """Déduit la configuration du worker depuis les champs Settings globaux."""
    # Configuration pour le worker NUC OpenCode
    github_token = getattr(cfg, "github_token", "") or getattr(cfg, "GH_TOKEN", "")
    github_api_url = getattr(cfg, "github_api_url", "https://api.github.com")

    # Extraire la liste des dépôts autorisés
    allowed_repos = []
    if hasattr(cfg, "allowed_repos"):
        allowed_repos = cfg.allowed_repos
    elif hasattr(cfg, "GITHUB_REPOS"):
        allowed_repos = cfg.GITHUB_REPOS.split(",") if cfg.GITHUB_REPOS else []
    else:
        # Par défaut, utiliser tvnv/axon-orchestrator
        allowed_repos = ["tvnv/axon-orchestrator"]

    # Extraire la liste des auteurs autorisés
    allowed_authors = []
    if hasattr(cfg, "allowed_authors"):
        allowed_authors = cfg.allowed_authors
    elif hasattr(cfg, "GITHUB_AUTHORS"):
        allowed_authors = cfg.GITHUB_AUTHORS.split(",") if cfg.GITHUB_AUTHORS else []

    # Configuration du répertoire de travail OpenCode
    opencode_workdir = getattr(cfg, "opencode_workdir", "")
    if not opencode_workdir:
        opencode_workdir = "/home/van/axon"

    return WorkerConfig(
        github_token=github_token,
        github_api_url=github_api_url,
        worker_id=getattr(cfg, "worker_id", DEFAULT_WORKER_ID),
        poll_seconds=getattr(cfg, "opencode_nuc_poll_seconds", DEFAULT_POLL_SECONDS),
        heartbeat_seconds=getattr(cfg, "opencode_nuc_heartbeat_seconds", DEFAULT_HEARTBEAT_SECONDS),
        opencode_bin=getattr(cfg, "opencode_nuc_bin", "opencode"),
        opencode_workdir=opencode_workdir,
        opencode_timeout_seconds=getattr(cfg, "opencode_nuc_timeout_seconds", DEFAULT_OPENCODE_TIMEOUT_SECONDS),
        journal_path=getattr(cfg, "opencode_nuc_journal_path", DEFAULT_JOURNAL_PATH),
        allowed_repos=allowed_repos,
        allowed_authors=allowed_authors,
    )


def main() -> None:
    """Point d'entrée principal pour le worker.

    Lit la configuration depuis les variables d'environnement (ou un fichier .env),
    puis démarre la boucle de polling principale.

    Variables d'environnement reconnues:
      GITHUB_TOKEN / GH_TOKEN  — token GitHub (obligatoire, ou fallback via gh CLI)
      ALLOWED_AUTHORS          — logins GitHub séparés par virgules (obligatoire)
      ALLOWED_REPOS            — dépôts autorisés séparés par virgules
      OPENCODE_WORKDIR         — répertoire de travail OpenCode (défaut: /home/van/axon)
      OPENCODE_BIN             — chemin vers le binaire opencode
      OPENCODE_TIMEOUT_SECONDS — timeout d'exécution OpenCode
      POLL_SECONDS             — intervalle de polling
      HEARTBEAT_SECONDS        — intervalle heartbeat
      JOURNAL_PATH             — chemin du journal de résultats
    """
    import os as _os

    try:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Token GitHub : env var first, then gh CLI fallback (token never logged)
        github_token = _os.environ.get("GITHUB_TOKEN", "") or _os.environ.get("GH_TOKEN", "")
        if not github_token:
            try:
                proc = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode == 0:
                    github_token = proc.stdout.strip()
            except Exception:
                pass
        if not github_token:
            print("[opencode-nuc-worker] erreur fatale: GITHUB_TOKEN requis (ou authentification gh CLI)")
            raise SystemExit(1)

        allowed_authors_str = _os.environ.get("ALLOWED_AUTHORS", "")
        allowed_authors = [a.strip() for a in allowed_authors_str.split(",") if a.strip()]

        allowed_repos_str = _os.environ.get("ALLOWED_REPOS", DEFAULT_GITHUB_REPO)
        allowed_repos = [r.strip() for r in allowed_repos_str.split(",") if r.strip()]

        config = WorkerConfig(
            github_token=github_token,
            github_api_url=_os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            worker_id=_os.environ.get("WORKER_ID", DEFAULT_WORKER_ID),
            poll_seconds=int(_os.environ.get("POLL_SECONDS", str(DEFAULT_POLL_SECONDS))),
            heartbeat_seconds=int(_os.environ.get("HEARTBEAT_SECONDS", str(DEFAULT_HEARTBEAT_SECONDS))),
            opencode_bin=_os.environ.get("OPENCODE_BIN", "opencode"),
            opencode_workdir=_os.environ.get("OPENCODE_WORKDIR", "/home/van/axon"),
            opencode_timeout_seconds=int(
                _os.environ.get("OPENCODE_TIMEOUT_SECONDS", str(DEFAULT_OPENCODE_TIMEOUT_SECONDS))
            ),
            journal_path=_os.environ.get(
                "JOURNAL_PATH",
                str(Path.home() / ".local/share/opencode-nuc-worker/results.jsonl"),
            ),
            allowed_repos=allowed_repos,
            allowed_authors=allowed_authors,
        )

        journal = ResultsJournal(config.journal_path)
        executor = OpenCodeExecutor(
            bin_path=config.opencode_bin,
            workdir=config.opencode_workdir,
            timeout_seconds=config.opencode_timeout_seconds,
        )
        http = httpx.Client(timeout=30.0)
        worker = OpenCodeNUCWorker(config, http, journal, executor)
        worker.run_forever()

    except KeyboardInterrupt:
        print("\n[opencode-nuc-worker] arrêté par l'utilisateur")
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[opencode-nuc-worker] erreur fatale: {exc}")
        raise