#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_DIR="$ROOT_DIR/fixtures/sample_app"
TEMP_DIR="$(mktemp -d)"
REPO_DIR="$TEMP_DIR/sample_app_repo"
APP_ID="sample-app"
REF="main"

cleanup() {
  if [[ -d "$REPO_DIR" ]]; then
    rm -rf "$REPO_DIR"
  fi
}
trap cleanup EXIT

mkdir -p "$REPO_DIR"
cp -R "$FIXTURE_DIR"/. "$REPO_DIR"/

pushd "$REPO_DIR" >/dev/null

if command -v git >/dev/null 2>&1; then
  git init -q
  git add .
  git commit -qm "sample app fixture"
  git branch -M "$REF"
else
  echo "git est requis pour le test de déploiement" >&2
  exit 1
fi

popd >/dev/null

export IKOMA_GIT_REMOTE="$REPO_DIR"
echo "IKOMA_GIT_REMOTE=$IKOMA_GIT_REMOTE"
echo "apps.register indisponible ; appel direct de deploy_up"
rm -rf "$ROOT_DIR/data/repos/$APP_ID"

python - <<'PY'
import sqlite3
from core.deploy import deploy_up
from core.deploy.deploy_up import DB_PATH

deploy_up("sample-app", "main")

with sqlite3.connect(DB_PATH) as conn:
    row = conn.execute(
        "SELECT app_id, ref, status, message FROM deployments WHERE app_id=?", ("sample-app",)
    ).fetchone()

print(f"Statut final : {row}")
PY

REPO_CLONE="$ROOT_DIR/data/repos/$APP_ID"
if [[ -f "$REPO_CLONE/docker-compose.yml" ]]; then
  docker compose -f "$REPO_CLONE/docker-compose.yml" down -v
fi
