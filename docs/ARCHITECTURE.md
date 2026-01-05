# Architecture IKOMA BRIDGE

## Rôle du Bridge
IKOMA BRIDGE fusionne les capacités de génération de MCP et le déploiement automatisé d'IKOMA Deployer pour offrir un chemin de publication unique : depuis la rédaction dans Lovable jusqu'au déploiement sur un VPS. Le Bridge agit comme orchestrateur unique des artefacts (contenu, infrastructure as code, conteneurs) et des opérations (build, tests, déploiement), sans interface graphique, en privilégiant des interactions API et CLI.

## Flux Lovable → GitHub → VPS
1. **Lovable (MCP)** : création/édition des contenus et assets via les outils MCP. Les changements sont versionnés localement puis poussés vers GitHub.
2. **GitHub** : héberge le dépôt fusionné. Les PR déclenchent la CI (tests, lint, build) et produisent des artefacts prêts à déployer. Les actions CI publient les images (ou bundles) dans un registre privé et marquent les releases.
3. **VPS (IKOMA Deployer)** : un agent de déploiement récupère les artefacts approuvés (release/tag), applique l'infra (Docker Compose/Ansible/Terraform), exécute les migrations et vérifie la santé. Les logs d'exécution sont renvoyés à l'API du Bridge pour observabilité.

## Arborescence du dépôt
```
/ (racine)
├── README.md              # Présentation courte et usages prévus
├── docs/                  # Guides d'architecture, roadmap, ADR et runbooks
│   ├── ARCHITECTURE.md    # Présent document
│   ├── ROADMAP.md         # Jalons v1, v1.1, v2
│   ├── adr/               # Architecture Decision Records
│   └── runbooks/          # Procédures incidents & opérations
├── api/                   # Entrée serveur API (app.py) + implémentations futures
├── cli/                   # Outils CLI (exécutable ikoma) pour opérateurs et CI
├── core/                  # Logique métier partagée (pipelines, orchestrateurs)
│   ├── pipelines/         # Orchestration des flux (Lovable → GitHub, GitHub → VPS)
│   ├── deployer/          # Intégration IKOMA Deployer (infra, runtime)
│   ├── mcp/               # Intégration MCP (outils Lovable, auth, contenu)
│   ├── adapters/          # Ports/Adapters pour SCM, Registry, Notifications
│   └── services/          # Interfaces supabase/backup/restore et helpers associés
├── infra/                 # IaC et packaging (Terraform/Ansible/Dockerfiles)
├── .github/workflows/     # Pipelines CI/CD GitHub Actions
└── scripts/               # Scripts utilitaires (bootstrap, check local)
```

## Modules clés (cible)
- **API Service (`api/`)** : endpoints pour déclencher les pipelines (build, déploiement), consulter l'état, récupérer les logs et notifier les statuts. Authentification (token/service) et quotas.
- **CLI Opérateur (`cli/`)** : commandes `bridge pipeline run`, `bridge deploy apply`, `bridge status` pour déclencher/inspecter depuis un poste ou la CI. Supporte les contextes (environnements) et les secrets locaux.
- **Core Pipelines (`core/pipelines/`)** : orchestration déclarative des étapes : checkout GitHub, build, tests, push image, release/tag, notification, déclenchement du déploiement sur VPS. Idempotence et reprise sur erreur.
- **Intégration MCP (`core/mcp/`)** : connexion aux outils Lovable/MCP (auth, sync contenus), gestion des drafts, push vers GitHub, contrôle des métadonnées de version.
- **Intégration Deployer (`core/deployer/`)** : pilotage du déploiement sur VPS (Docker Compose, migrations, hooks pré/post), validation post-déploiement et rollback.
- **Adaptateurs (`core/adapters/`)** : abstractions SCM (GitHub), registre d'images, stockage d'artefacts, bus d'événements/notifications (Slack/Webhook), observabilité.
- **Services (`core/services/`)** : interfaces pour les dépendances techniques clés (supabase.ensure, backup/restore) et helpers transverses.
- **Infra (`infra/`)** : définition des stacks (prod/preprod), secrets/backends, modèles de release (images, manifests), et configuration de l'agent Deployer.

## Composants API / CLI / Core
- **API** : services HTTP exposant les endpoints publics/privés pour exécuter les pipelines, récupérer les statuts et logs, gérer les secrets et les environnements. Conçue pour être stateless (backend DB/queue séparé).
- **CLI** : interface ligne de commande utilisée par les développeurs, opérateurs et pipelines CI pour déclencher ou auditer les processus du Bridge. Offre des commandes de diagnostic local et la génération de bundles prêts à pousser vers le Bridge.
- **Core** : coeur métier et orchestrateurs communs. Implémente les pipelines, gère les événements, coordonne les adaptateurs et applique les politiques (retraits automatiques, fenêtres de déploiement, garde-fous de migration).
