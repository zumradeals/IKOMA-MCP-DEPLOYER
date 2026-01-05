# Roadmap IKOMA BRIDGE

## v1 (MVP déploiement automatisé)
- Pipeline GitHub → VPS pour un service unique (build, push image, déploiement via Deployer).
- CLI de déclenchement manuel (`deploy up`, `deploy rollback`).
- API minimale : healthcheck, déclenchement déploiement, récupération des journaux récents.
- Observabilité de base : logs textuels, retours d'état synchrones.

## v1.1 (Robustesse et intégrations)
- Support multi-services / multi-environnements avec templates d'infra.
- Sécurisation : authentification token/clé API côté API et CLI.
- Gestion Supabase : vérification/initialisation automatique des ressources nécessaires.
- Backups automatisés avec planification et stockage distant configurable.
- Notifications (Slack/Webhook) sur succès/échec des pipelines.

## v2 (Industrialisation)
- Orchestration complète Lovable → GitHub → VPS (incluant validations, PR gating, promotions d'environnements).
- File d'attente/queue pour exécutions parallèles et reprise sur incident.
- Portail d'observabilité API/CLI : historique, métriques, rapports.
- Catalogue d'adaptateurs (SCM, registre, stockage, notifications) et contrat de plug-ins.
- Politique avancée de rollback/migrations avec étapes de validation automatisées.
