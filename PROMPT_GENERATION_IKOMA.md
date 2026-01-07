# Prompt de Génération Standard IKOMA (Runner-Ready)

Ce document définit les règles impératives pour la génération d'applications compatibles avec l'écosystème IKOMA (Runner + Gateway). Toute application générée doit respecter strictement ce contrat d'architecture.

## 1. Architecture Réseau & Docker

L'application ne doit jamais tenter de gérer elle-même son exposition publique, ses domaines ou ses certificats SSL.

### Docker Compose (`docker-compose.yml`)
- **INTERDICTION ABSOLUE** : Ne jamais binder les ports `80` ou `443` sur l'hôte.
- **RÈGLE** : L'application doit écouter sur un port local uniquement.
- **CONFIGURATION RECOMMANDÉE** :
  ```yaml
  services:
    web:
      # ... build/image ...
      expose:
        - "3000" # Port interne du conteneur
      ports:
        - "127.0.0.1:3010:3000" # Bind local uniquement (optionnel si Gateway utilise le réseau Docker)
  ```

## 2. Manifeste de Déploiement (`ikoma.release.json`)

Chaque application doit inclure à sa racine un fichier `ikoma.release.json` conforme au schéma suivant :

```json
{
  "compose": "docker-compose.yml",
  "services": ["web"],
  "health": {
    "type": "http",
    "url": "/"
  }
}
```

### Spécifications du Manifeste :
- `compose` : Nom du fichier Docker Compose (généralement `docker-compose.yml`).
- `services` : Liste des services à démarrer (ex: `["web"]`).
- `health` : Objet JSON définissant le test de santé.
  - `type` : Doit être `"http"`.
  - `url` : Chemin relatif pour le healthcheck (ex: `"/"` ou `"/health"`). **Obligatoire et non vide**.

## 3. Responsabilités des Composants

- **IKOMA Runner** : Gère exclusivement le cycle de vie technique (clone, build, deploy, migrate).
- **IKOMA Gateway** : Gère exclusivement la couche d'accès (domaines, sous-domaines, SSL, reverse-proxy).
- **L'Application** : Doit être un service HTTP neutre, portable et sans logique spécifique à l'infrastructure.

## 4. Interdictions Formelles

Lors de la génération, il est strictement interdit de :
- Ajouter des services de reverse-proxy (Nginx, Caddy, Traefik) dans le `docker-compose.yml`.
- Inclure des scripts de gestion de certificats (Certbot, Let's Encrypt).
- Tenter de modifier la configuration d'IKOMA Gateway ou d'IKOMA Runner.
- Ajouter des champs "intelligents" ou non documentés dans `ikoma.release.json`.
