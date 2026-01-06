Rôle d’Architecte Cognitif IA activé. Doctrine et Phasage intégrés.

Parfait. Snapshot fait = **ligne de non-retour sécurisée**.
On peut maintenant figer un **runbook clair, opérable et durable**.

---

# 📘 RUNBOOK IKOMA

## Déploiement d’une App IA souveraine (v1)

**Objectif**
Déployer une application conçue par une IA Dev (Lovable, Bolt, autre) sur un **VPS souverain**, avec :

* base Supabase **self-host**
* migrations SQL versionnées
* déploiement Docker Compose
* traçabilité et statut de déploiement

Ce runbook est conçu pour :

* toi aujourd’hui
* un collaborateur demain
* une exécution sans improvisation

---

## 1️⃣ Périmètre et hypothèses

### Ce que fait ce runbook

* Reconstruit la base de données via migrations SQL
* Déploie l’application via Docker Compose
* Vérifie l’état de santé
* Enregistre le statut

### Ce que ce runbook ne fait PAS

* Installer Supabase (déjà installé)
* Gérer les backups avancés
* Gérer le rollback
* Fournir une UI

---

## 2️⃣ Prérequis obligatoires

### Infrastructure

* VPS Linux (Ubuntu recommandé)
* Docker + Docker Compose installés
* Supabase self-host **fonctionnel**
* Accès root ou sudo

### Logiciel IKOMA

* Répertoire : `/opt/IKOMA-MCP-DEPLOYER`
* Environnement virtuel Python prêt : `.venv`
* CLI `cli/ikoma` fonctionnelle

### Application à déployer

* Repo Git cloné localement (ex: `/opt/ikomaposte`)
* Contient :

  * `docker-compose.yml`
  * `ikoma.release.json`
  * dossier `migrations/` (SQL versionnés)

---

## 3️⃣ Préparation de la session opérateur

Toujours commencer ici.

```bash
cd /opt/IKOMA-MCP-DEPLOYER
source .venv/bin/activate
export PYTHONPATH=/opt/IKOMA-MCP-DEPLOYER
```

---

## 4️⃣ Configuration des variables critiques

### Connexion à la base Supabase (PostgreSQL)

```bash
export SUPABASE_DB_DSN="postgresql://USER:PASSWORD@127.0.0.1:5432/postgres"
```

⚠️ Le mot de passe n’apparaît jamais dans les logs.

Optionnel (si schéma différent) :

```bash
export SUPABASE_DB_SCHEMA="public"
```

---

## 5️⃣ Reconstruction de la base (migrations)

### Commande officielle

```bash
python cli/ikoma supabase migrate \
  --app ikomaposte \
  --repo /opt/ikomaposte
```

### Résultat attendu

* Logs du type :

  ```
  Application de 0001_*.sql
  ...
  Migration Supabase terminée
  ```
* Aucune erreur bloquante
* Les migrations sont enregistrées (idempotence assurée)

👉 Cette étape **prouve la sortie du lock-in**.

---

## 6️⃣ Déploiement de l’application

### Commande

```bash
python cli/ikoma deploy up \
  --app ikomaposte \
  --ref main
```

### Ce que fait le système

* Clone / synchronise le repo
* Lit `ikoma.release.json`
* Lance `docker compose up -d`
* Attend le healthcheck
* Trace les logs
* Enregistre le statut

---

## 7️⃣ Vérifications post-déploiement

### Vérifier l’état enregistré

* Statut attendu : `HEALTHY`
* Message : `Déploiement validé par healthcheck`

### Vérifier les containers

```bash
docker ps
```

### Vérifier l’endpoint santé

```bash
curl http://localhost:<port>/health
```

---

## 8️⃣ Nettoyage (si test)

Si c’était un test (fixture, staging) :

```bash
docker compose down -v
```

Ou suppression ciblée du repo déployé :

```bash
rm -rf /opt/IKOMA-MCP-DEPLOYER/data/repos/ikomaposte
```

---

## 9️⃣ Critères de succès (verrouillés)

Le déploiement est **validé** si :

* ✅ migrations appliquées sans erreur
* ✅ application démarrée
* ✅ healthcheck OK
* ✅ aucune dépendance à Lovable / Supabase managé
* ✅ état traçable dans IKOMA

---

## 🔐 Principe fondamental IKOMA (à retenir)

> **Une app n’est considérée “déployée”
> que si sa base peut être reconstruite ailleurs.**

Ce runbook est la **preuve opérationnelle** de cette règle.

---

## État final du système (v1)

À partir d’aujourd’hui, IKOMA dispose :

* d’un **socle de déploiement souverain**
* d’une **procédure reproductible**
* d’une **méthode transmissible**

👉 La phase **MODE CONCEPTION** est respectée.
👉 Aucun MODE BUILD prématuré n’a été déclenché.

---

Quand tu veux, prochaine étape possible (au choix, et **pas obligatoire**) :

* Runbook v2 (backup / restore)
* Runbook multi-apps
* Verrouillage “release.json” comme contrat
* Ou pause stratégique (ce qui est aussi une décision valide)

Tu as maintenant **un système qui tient debout sans toi**. C’est le vrai marqueur de maturité.
