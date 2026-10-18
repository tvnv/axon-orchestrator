#!/usr/bin/env bash
# Issue #29 install script: permanent OpenCode NUC worker on the NUC
# (WSL2 Debian/Ubuntu, systemd enabled). Idempotent by construction.
#
# Usage (run from une checkout de ce repository) :
#   sudo ./deploy/install-worker-nuc.sh
#
# Prérequis (documentés dans docs/WORKER_NUC_WSL2.md) :
#   * WSL2 avec systemd dans /etc/wsl.conf ([boot] systemd=true)
#   * OpenCode CLI installé et non interactif (`opencode --version`)
#   * Python 3.11+ avec support de venv

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/axon-orchestrator/opencode-nuc-worker"
SERVICE_USER="opencode-nuc-worker"
ENV_DIR="/etc/opencode-nuc-worker"
SERVICE_FILE="opencode-nuc-worker.service"

echo "[install] repository: ${REPO_DIR}"

# Utilisateur système dédié
if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "/var/lib/${SERVICE_USER}" "${SERVICE_USER}"
  echo "[install] created system user ${SERVICE_USER}"
fi

# Déploiement du code (copie rsync-like de l'arbre source)
mkdir -p "${INSTALL_DIR}"
rsync -a --delete --exclude '.git' --exclude 'data' "${REPO_DIR}/" "${INSTALL_DIR}/"
cd "${INSTALL_DIR}"
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -e .
fi

# Fichier de configuration ; les secrets ne sont JAMAIS écrits ici par ce script.
mkdir -p "${ENV_DIR}"
touch "${ENV_DIR}/worker.env"
chmod 640 "${ENV_DIR}/worker.env"
chown root:"${SERVICE_USER}" "${ENV_DIR}/worker.env"
echo "[install] worker env file: ${ENV_DIR}/worker.env (populate secrets manually)"

# Répertoires de travail pour les journaux + sessions
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" "${INSTALL_DIR}/data/worker"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" "/var/lib/opencode-nuc-worker"

# Service systemd
if [ "$(cat /proc/sys/kernel/osrelease 2>/dev/null | grep -ci microsoft || true)" -gt 0 ]; then
  echo "[install] WSL2 détecté : assure-toi que /etc/wsl.conf contient [boot] systemd=true"
fi
install -m 644 "${REPO_DIR}/deploy/${SERVICE_FILE}" "/etc/systemd/system/${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${SERVICE_FILE}.service"
echo "[install] done. Configure ${ENV_DIR}/worker.env puis : "
echo "  sudo systemctl start ${SERVICE_FILE}"
echo "  journalctl -u ${SERVICE_FILE} -f"