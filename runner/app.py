from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.deploy import deploy_up
from core.deploy.deploy_up import DB_PATH, LOGS_DIR
from core.logging.logger import build_logger
from core.scm.git_repo import sync_repository
from core.services.supabase import supabase_apply_migrations
from runner.config_store import AppConfig, AppConfigStore

app = FastAPI(title="IKOMA Runner UI", version="0.0.1")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
config_store = AppConfigStore(DB_PATH)


# --- Helpers ---
def _ensure_schema() -> None:
    from core.store.sqlite_store import DeploymentState

    DeploymentState(DB_PATH).ensure_schema()


def _fetch_configs() -> List[AppConfig]:
    return config_store.list_configs()


def _get_config(app_id: str) -> Optional[AppConfig]:
    return config_store.get(app_id)


def _fetch_deployments() -> List[Dict[str, Any]]:
    _ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT app_id, ref, status, message, updated_at FROM deployments ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def _fetch_deployment(app_id: str) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT app_id, ref, status, message, updated_at FROM deployments WHERE app_id = ?",
            (app_id,),
        ).fetchone()
        return dict(row) if row else None


def _fetch_supabase_run(app_id: str) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT app_id, status, message, updated_at, migrations FROM supabase_runs WHERE app_id = ?",
            (app_id,),
        ).fetchone()
        return dict(row) if row else None


def _get_logs(app_id: str) -> List[Path]:
    app_log_dir = LOGS_DIR / app_id
    if not app_log_dir.exists():
        return []
    return [p for p in app_log_dir.iterdir() if p.is_file() and p.suffix == ".log"]


@contextmanager
def _with_git_remote(remote_url: str):
    previous = os.environ.get("IKOMA_GIT_REMOTE")
    os.environ["IKOMA_GIT_REMOTE"] = remote_url
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("IKOMA_GIT_REMOTE", None)
        else:
            os.environ["IKOMA_GIT_REMOTE"] = previous


def _start_thread(target: Any, *, args: tuple) -> None:
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()


def _default_path(app_id: str) -> str:
    return f"/opt/{app_id}"


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def index(request: Request, status: str | None = None, message: str | None = None) -> HTMLResponse:
    configs = _fetch_configs()
    deployments = {dep["app_id"]: dep for dep in _fetch_deployments()}
    context = {
        "request": request,
        "configs": configs,
        "deployments": deployments,
        "count": len(configs),
        "status_message": status,
        "status_detail": message,
    }
    return templates.TemplateResponse("index.html", context)


@app.post("/apps")
def create_app(
    app_id: str = Form(...),
    repo_git_url: str = Form(...),
    branch: str = Form("main"),
    path_deploiement: str = Form(""),
    migrations_dir: str = Form(""),
    type_app: str = Form("generic"),
) -> RedirectResponse:
    cleaned_app_id = app_id.strip()
    cleaned_repo = repo_git_url.strip()
    if not cleaned_app_id:
        raise HTTPException(status_code=400, detail="app_id est requis")
    if not cleaned_repo:
        raise HTTPException(status_code=400, detail="repo_git_url est requis")

    cleaned_branch = branch.strip() or "main"
    cleaned_path = path_deploiement.strip() or _default_path(cleaned_app_id)
    cleaned_migrations = migrations_dir.strip()
    cleaned_type = type_app.strip() or "generic"

    config_store.upsert(
        AppConfig(
            app_id=cleaned_app_id,
            repo_git_url=cleaned_repo,
            branch=cleaned_branch,
            path_deploiement=cleaned_path,
            migrations_dir=cleaned_migrations,
            type_app=cleaned_type,
        )
    )

    return RedirectResponse(
        url=f"/apps/{quote(cleaned_app_id)}?status=config_saved&message=Application%20enregistr%C3%A9e",
        status_code=303,
    )


@app.get("/apps/{app_id}", response_class=HTMLResponse)
def app_detail(request: Request, app_id: str, status: str | None = None, message: str | None = None) -> HTMLResponse:
    config = _get_config(app_id)
    if not config:
        raise HTTPException(status_code=404, detail="Application inconnue")

    deployment = _fetch_deployment(app_id)
    supabase_run = _fetch_supabase_run(app_id)
    logs = _get_logs(app_id)
    context = {
        "request": request,
        "app_id": app_id,
        "config": config,
        "deployment": deployment,
        "supabase_run": supabase_run,
        "logs": logs,
        "status_message": status,
        "status_detail": message,
    }
    return templates.TemplateResponse("app_detail.html", context)


@app.post("/apps/{app_id}/update")
def update_app(
    app_id: str,
    repo_git_url: str = Form(...),
    branch: str = Form("main"),
    path_deploiement: str = Form(""),
    migrations_dir: str = Form(""),
    type_app: str = Form("generic"),
) -> RedirectResponse:
    config = _get_config(app_id)
    if not config:
        raise HTTPException(status_code=404, detail="Application inconnue")

    cleaned_repo = repo_git_url.strip()
    if not cleaned_repo:
        raise HTTPException(status_code=400, detail="repo_git_url est requis")

    config_store.upsert(
        AppConfig(
            app_id=app_id,
            repo_git_url=cleaned_repo,
            branch=branch.strip() or config.branch,
            path_deploiement=path_deploiement.strip() or _default_path(app_id),
            migrations_dir=migrations_dir.strip(),
            type_app=type_app.strip() or config.type_app,
        )
    )

    return RedirectResponse(
        url=f"/apps/{quote(app_id)}?status=config_saved&message=Configuration%20mise%20%C3%A0%20jour",
        status_code=303,
    )


@app.post("/apps/{app_id}/sync")
def trigger_sync(app_id: str) -> RedirectResponse:
    config = _get_config(app_id)
    if not config:
        raise HTTPException(status_code=404, detail="Application inconnue")

    target_dir = Path(config.path_deploiement or _default_path(app_id)).expanduser()
    repo_base = target_dir.parent
    branch = config.branch or "main"

    def _run() -> None:
        logger = build_logger(app_id, LOGS_DIR, log_filename="sync.log")
        try:
            with _with_git_remote(config.repo_git_url):
                sync_repository(app_id, branch, repo_base, logger)
        except Exception:
            # sync_repository trace déjà dans les logs
            pass

    _start_thread(_run, args=())
    return RedirectResponse(
        url=(
            f"/apps/{quote(app_id)}?status=sync_started"
            f"&message=Synchronisation%20git%20lanc%C3%A9e%20({quote(branch)})"
        ),
        status_code=303,
    )


@app.post("/apps/{app_id}/deploy")
def trigger_deploy(app_id: str, ref: str = Form("")) -> RedirectResponse:
    config = _get_config(app_id)
    if not config:
        raise HTTPException(status_code=404, detail="Application inconnue")

    chosen_ref = ref.strip() or config.branch or "main"
    if not chosen_ref:
        raise HTTPException(status_code=400, detail="ref est requis")

    def _run() -> None:
        try:
            with _with_git_remote(config.repo_git_url):
                deploy_up(app_id, chosen_ref)
        except Exception:
            # deploy_up trace déjà dans les logs
            pass

    _start_thread(_run, args=())
    return RedirectResponse(
        url=(
            f"/apps/{quote(app_id)}?status=deploy_started"
            f"&message=D%C3%A9ploiement%20lanc%C3%A9%20pour%20{quote(chosen_ref)}"
        ),
        status_code=303,
    )


@app.post("/apps/{app_id}/migrate")
def trigger_migration(
    app_id: str,
    repo_path: str = Form(""),
    migrations_dir: str = Form(""),
) -> RedirectResponse:
    config = _get_config(app_id)
    if not config:
        raise HTTPException(status_code=404, detail="Application inconnue")

    cleaned_repo = repo_path.strip() or config.path_deploiement or _default_path(app_id)
    cleaned_dir = migrations_dir.strip() or config.migrations_dir or "supabase/migrations"

    def _run() -> None:
        try:
            supabase_apply_migrations(app_id, Path(cleaned_repo), cleaned_dir)
        except Exception:
            # supabase_apply_migrations trace déjà dans les logs
            pass

    _start_thread(_run, args=())
    encoded_dir = quote(cleaned_dir)
    return RedirectResponse(
        url=(
            f"/apps/{quote(app_id)}?status=migrate_started"
            f"&message=Migration%20lanc%C3%A9e%20({encoded_dir})"
        ),
        status_code=303,
    )


@app.get("/apps/{app_id}/logs/{log_name}", response_class=PlainTextResponse)
def view_log(app_id: str, log_name: str) -> PlainTextResponse:
    safe_names = {"deploy.log", "supabase.log", "sync.log"}
    if log_name not in safe_names:
        raise HTTPException(status_code=404, detail="Log inconnu")

    log_path = LOGS_DIR / app_id / log_name
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Fichier de log introuvable")

    content = log_path.read_text(encoding="utf-8", errors="replace")
    return PlainTextResponse(content)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
