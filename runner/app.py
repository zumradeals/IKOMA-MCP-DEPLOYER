from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.deploy import deploy_up
from core.deploy.deploy_up import DB_PATH, LOGS_DIR
from core.services.supabase import supabase_apply_migrations

app = FastAPI(title="IKOMA Runner UI", version="0.0.1")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


# --- Helpers ---
def _ensure_schema() -> None:
    from core.store.sqlite_store import DeploymentState

    DeploymentState(DB_PATH).ensure_schema()


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


def _start_thread(target: Any, *, args: tuple) -> None:
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    deployments = _fetch_deployments()
    context = {
        "request": request,
        "deployments": deployments,
        "count": len(deployments),
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/apps/{app_id}", response_class=HTMLResponse)
def app_detail(request: Request, app_id: str, status: str | None = None, message: str | None = None) -> HTMLResponse:
    deployment = _fetch_deployment(app_id)
    supabase_run = _fetch_supabase_run(app_id)
    logs = _get_logs(app_id)
    context = {
        "request": request,
        "app_id": app_id,
        "deployment": deployment,
        "supabase_run": supabase_run,
        "logs": logs,
        "status_message": status,
        "status_detail": message,
    }
    return templates.TemplateResponse("app_detail.html", context)


@app.post("/apps/{app_id}/deploy")
def trigger_deploy(app_id: str, ref: str = Form("main")) -> RedirectResponse:
    if not ref.strip():
        raise HTTPException(status_code=400, detail="ref est requis")

    def _run() -> None:
        try:
            deploy_up(app_id, ref.strip())
        except Exception:
            # deploy_up trace déjà dans les logs
            pass

    _start_thread(_run, args=())
    return RedirectResponse(
        url=f"/apps/{app_id}?status=deploy_started&message=Déploiement%20lancé%20pour%20{ref.strip()}",
        status_code=303,
    )


@app.post("/apps/{app_id}/migrate")
def trigger_migration(
    app_id: str,
    repo_path: str = Form(...),
    migrations_dir: str = Form("supabase/migrations"),
) -> RedirectResponse:
    cleaned_repo = repo_path.strip()
    if not cleaned_repo:
        raise HTTPException(status_code=400, detail="repo_path est requis")
    cleaned_dir = migrations_dir.strip() or "supabase/migrations"

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
            f"/apps/{app_id}?status=migrate_started"
            f"&message=Migration%20lancée%20({encoded_dir})"
        ),
        status_code=303,
    )


@app.get("/apps/{app_id}/logs/{log_name}", response_class=PlainTextResponse)
def view_log(app_id: str, log_name: str) -> PlainTextResponse:
    safe_names = {"deploy.log", "supabase.log"}
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
