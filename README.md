# IKOMA BRIDGE

Fusion opérée entre IKOMA MCP (génération) et IKOMA Deployer (exécution), IKOMA BRIDGE fournit un chemin unique du contenu Lovable jusqu'au déploiement sur VPS.

## État du projet
- **Phase** : ossature initiale (interfaces et stubs).
- **UI** : aucune interface graphique n'est prévue.
- **Cible** : interactions via API et CLI uniquement.

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

### Migrations Supabase (instance self-host existante)
Une commande CLI applique les fichiers `.sql` d'une application sur une instance Supabase déjà déployée :

```bash
./cli/ikoma supabase migrate --app <app_id> --repo /chemin/vers/le/repo
```

Variables de connexion supportées :
- `SUPABASE_DB_DSN` (DSN Postgres complet) ;
- ou les variables `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`.

Les migrations sont appliquées dans l'ordre lexicographique depuis `supabase/migrations`, chaque fichier étant exécuté dans une transaction et enregistré dans la table `ikoma_migrations`. Les résultats sont tracés dans `data/logs/<app_id>/supabase.log` et le statut final est consigné dans `data/ikoma.db`.

Consultez `docs/ARCHITECTURE.md` pour la vision complète et `docs/ROADMAP.md` pour les jalons à venir.
