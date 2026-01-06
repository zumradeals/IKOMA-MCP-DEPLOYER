# IKOMA BRIDGE

Fusion opérée entre IKOMA MCP (génération) et IKOMA Deployer (exécution), IKOMA BRIDGE fournit un chemin unique du contenu Lovable jusqu'au déploiement sur VPS.

## État du projet
- **Phase** : ossature initiale (interfaces et stubs).
- **UI** : interface minimale IKOMA Runner disponible (FastAPI + templates).
- **Cible** : interactions via API et CLI uniquement.

## IKOMA RUNNER (UI Phase 0)
Une interface web minimale est disponible pour piloter les actions manuelles :

```bash
pip install -r requirements.txt
scripts/run_runner.sh  # démarre uvicorn runner.app:app sur :8088 par défaut
```

Elle liste les applications connues (SQLite `data/ikoma.db`) et permet de déclencher `deploy_up` et `supabase_apply_migrations` sans ajouter de logique métier.

## Usage (prévu)
- **CLI** : l'exécutable `cli/ikoma` proposera des commandes pour déclencher les pipelines, suivre les statuts et orchestrer les déploiements.
- **API** : le serveur `api/app.py` exposera des endpoints REST pour piloter le Bridge depuis des workflows ou intégrations tierces.

### Déploiement minimal (Docker Compose)
Une primitive fonctionnelle est disponible pour tester un déploiement simple :

```bash
export IKOMA_GIT_REMOTE="https://github.com/your-org/your-repo.git"
python -c "from core.deploy import deploy_up; deploy_up('demo-app', 'main')"
```

Conditions :
- le dépôt cible doit contenir un `ikoma.release.json` décrivant `compose_file`, `services` et `health.url` ;
- `docker compose` doit être disponible localement ;
- les logs sont écrits dans `data/logs/<app_id>/deploy.log` et le statut dans `data/ikoma.db`.


Consultez `docs/ARCHITECTURE.md` pour la vision complète et `docs/ROADMAP.md` pour les jalons à venir.
