import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from core.deploy import deploy_up


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker requis pour ce test")
def test_deploy_up_sample_app(tmp_path):
    root_dir = Path(__file__).resolve().parents[1]
    fixture_dir = root_dir / "fixtures" / "sample_app"

    repo_dir = tmp_path / "sample_app_repo"
    shutil.copytree(fixture_dir, repo_dir)

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "commit", "-m", "sample app"], cwd=repo_dir, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_dir, check=True, stdout=subprocess.DEVNULL)

    app_id = "sample-app"
    ref = "main"
    repos_dir = root_dir / "data" / "repos" / app_id
    if repos_dir.exists():
        shutil.rmtree(repos_dir)

    db_path = root_dir / "data" / "ikoma.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["IKOMA_GIT_REMOTE"] = str(repo_dir)

    try:
        deploy_up.deploy_up(app_id, ref)

        req = Request("http://localhost:8080/health", method="GET")
        with urlopen(req, timeout=5) as resp:  # nosec - URL locale contrôlée
            body = resp.read().decode("utf-8")
            assert resp.status == 200
            assert "ok" in body

        with sqlite3.connect(db_path) as conn:
            status = conn.execute(
                "SELECT status FROM deployments WHERE app_id=?", (app_id,)
            ).fetchone()
            assert status is not None
            assert status[0] == "HEALTHY"
    finally:
        if repos_dir.exists():
            compose_file = repos_dir / "docker-compose.yml"
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down", "-v"],
                cwd=repos_dir,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
