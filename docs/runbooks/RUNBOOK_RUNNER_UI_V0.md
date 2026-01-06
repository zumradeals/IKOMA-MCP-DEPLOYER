# IKOMA Runner UI (Phase 0)

## Lancement
- Installer les dépendances Python: `pip install -r requirements.txt`
- Démarrer l'UI: `scripts/run_runner.sh` (variables possibles: `PORT`, `HOST`, `UVICORN_CMD`).
- Service recommandé: `uvicorn runner.app:app --host 0.0.0.0 --port 8088`.

## Variables d'environnement
- `SUPABASE_DB_DSN`: DSN Postgres pour les migrations (obligatoire pour `supabase_apply_migrations`).
- `SUPABASE_DB_SCHEMA` (optionnel): schéma utilisé lors des migrations (par défaut `public`).

## Données et logs
- Base SQLite: `data/ikoma.db` (créée automatiquement si absente).
- Logs d'application: `data/logs/<app_id>/deploy.log` et `data/logs/<app_id>/supabase.log`.

## Endpoints
- `GET /`: liste des applications connues (table `deployments`).
- `GET /apps/{app_id}`: détail d'une app, derniers statuts, liens vers logs, formulaires.
- `POST /apps/{app_id}/deploy`: lance `deploy_up(app_id, ref)` (body: `ref`, défaut `main`).
- `POST /apps/{app_id}/migrate`: lance `supabase_apply_migrations(app_id, repo_path, migrations_dir)` (body: `repo_path`, `migrations_dir` défaut `supabase/migrations`).
- `GET /apps/{app_id}/logs/{log_name}`: affiche `deploy.log` ou `supabase.log` si présent.
- `GET /health`: ping simple.

## Notes
- L'UI n'ajoute pas de logique métier: elle déclenche les fonctions existantes et lit SQLite/logs.
- Les appels POST renvoient une redirection vers la page détail avec un message synthétique; les erreurs de validation retournent un code HTTP 400.
