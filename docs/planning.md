# Plateforme légère de gestion de findings de sécurité
## Cahier des charges condensé + Planning d'exécution

---

## 1. C'est quoi, en une phrase

Une petite application qui récupère les résultats de 3 scanners de sécurité (Semgrep, Trivy, Checkov), les met dans un format commun, évite les doublons, calcule un score de priorité, et dit à GitHub Actions si le build doit passer ou échouer.

**Objectif réel** : apprendre à construire un vrai système DevSecOps de A à Z, pas juste utiliser un outil existant. Projet pour votre PFE et votre CV.

---

## 2. Stack technique (figée, ne plus en discuter)

- Scanners : **Semgrep** (code), **Trivy** (dépendances/conteneurs), **Checkov** (infra as code)
- Format d'échange : **SARIF**
- Backend : **FastAPI + Pydantic**
- Base de données : **PostgreSQL + SQLAlchemy + Alembic**
- Frontend : **Jinja2** (pages simples générées par le serveur, pas de React)
- Déploiement local : **Docker Compose**
- CI/CD : **GitHub Actions**
- **Interdit** : Kubernetes, Redis, Celery, Kafka, microservices, IA/fuzzy matching

---

## 3. Ce que l'application doit faire (MVP = version minimale mais complète)

| Fonctionnalité | Description simple |
|---|---|
| Recevoir un rapport de scan | Un endpoint API qui reçoit le résultat JSON/SARIF d'un scanner |
| Comprendre chaque outil | Un "traducteur" par scanner qui transforme son format en un format commun |
| Éviter les doublons | Ne pas recréer le même problème à chaque scan |
| Suivre l'évolution | Savoir si un problème est nouveau, toujours là, ou corrigé |
| Calculer une priorité | Un score simple et explicable (pas magique) |
| Afficher les résultats | Une page web simple : liste des problèmes, compteurs, filtres |
| Bloquer ou non le build | Répondre PASS/FAIL à GitHub Actions |

Tout le reste (graphiques avancés, rapports PDF riches, IA, etc.) attend une V2 — **on ne s'en occupe pas maintenant.**

---

## 4. Planning — étape par étape

Chaque étape = un livrable concret et testable. On ne passe à l'étape suivante que quand celle d'avant fonctionne réellement (pas juste "écrite").

### Étape 0 — Squelette du projet (0,5 à 1 jour)
- Créer le dépôt Git.
- `docker-compose.yml` avec un conteneur FastAPI (vide, juste "hello world") + un conteneur PostgreSQL.
- **Fait quand** : `docker compose up` démarre les deux conteneurs sans erreur, et `curl localhost:8000` répond.

### Étape 1 — Base de données (1 à 2 jours)
- Créer les tables : `Project`, `Repository`, `ScanExecution`, `Finding`, `FindingOccurrence`, `RiskAssessment`.
- Migrations Alembic.
- **Fait quand** : les tables existent en base, on peut insérer/lire une ligne manuellement dans chacune.

### Étape 2 — Ingestion d'un rapport (2 à 3 jours)
- Endpoint `POST /scans` qui reçoit un fichier SARIF + métadonnées (repository, scanner, commit, branche, complet/partiel).
- Validation minimale : rejeter un JSON invalide, accepter un rapport vide.
- Stocker le rapport brut en base.
- **Fait quand** : on peut envoyer un vrai rapport Semgrep via `curl` et voir une ligne apparaître dans `ScanExecution`.

### Étape 3 — Premier adaptateur : Semgrep (2 à 3 jours)
- Transformer un rapport Semgrep en "Common Finding" (le format commun défini).
- Calculer l'identité stable de chaque finding.
- **Fait quand** : après ingestion d'un rapport Semgrep, des lignes apparaissent dans `Finding` avec les bons champs.

### Étape 4 — Deuxième et troisième adaptateurs : Trivy, Checkov (3 à 4 jours)
- Même travail que l'étape 3, pour les deux autres scanners.
- **Fait quand** : les trois scanners produisent des findings corrects et cohérents.

### Étape 5 — Déduplication et comparaison entre scans (2 à 3 jours)
- Un même scan rejoué deux fois ne crée pas de doublon.
- Un finding disparu d'un scan complet réussi passe à "corrigé".
- Un scan partiel ne change rien.
- **Fait quand** : ces 3 comportements sont vérifiés manuellement.

### Étape 6 — Score de risque (1 à 2 jours)
- Implémenter la formule définie (sévérité + CVSS si dispo + CWE + confiance).
- **Fait quand** : chaque finding a un score cohérent, visible en base.

### Étape 7 — Security Gate (1 jour)
- Endpoint qui répond PASS/FAIL pour un commit donné.
- FAIL si un scanner attendu manque.
- **Fait quand** : on peut tester manuellement les deux cas (tout est là → PASS ; un scanner manque → FAIL).

### Étape 8 — Interface web minimale (2 jours)
- Une page : liste des findings, compteurs par sévérité/statut, filtres simples.
- **Fait quand** : vous pouvez ouvrir un navigateur et voir vos findings.

### Étape 9 — Test Lab (2 à 3 jours)
- Un petit dépôt avec des vulnérabilités volontaires.
- Un script qui lance les 3 scanners, envoie les résultats, vérifie que tout marche comme prévu.
- **Fait quand** : le script tourne et confirme que le pipeline entier fonctionne de bout en bout.

### Étape 10 — Intégration GitHub Actions (1 à 2 jours)
- Un workflow qui lance les scanners sur chaque push, envoie les résultats, bloque le merge si FAIL.
- **Fait quand** : un vrai push sur GitHub déclenche tout automatiquement.

### Étape 11 — Documentation finale (2 jours)
- README, schéma d'architecture, limites connues, captures d'écran.
- **Fait quand** : quelqu'un d'autre pourrait installer et comprendre le projet en le lisant.

### Étape 12 — Mise en valeur CV/PFE (0,5 jour)
- Résumé du projet, compétences démontrées, points à mentionner en entretien.

---

## 5. Temps total estimé

Environ **20 à 25 jours de travail effectif** (pas calendaires) si vous suivez les étapes dans l'ordre, sans repartir dans une grosse phase de réflexion à chaque fois. Si vous avez une deadline précise, dites-la moi et on ajuste ce qui peut être coupé (ex. : ne garder que 2 scanners, simplifier le score).

---

## 6. Règle simple pour la suite

**Une étape à la fois.** Vous me dites "je suis à l'étape X, voilà où je bloque", et on résout juste ça — pas besoin de tout comprendre l'architecture globale pour avancer.
