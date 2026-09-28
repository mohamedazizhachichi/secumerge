# SecuMerge — Spécification du projet

> Document de référence complet : exigences, architecture, API, sécurité, tests, phases.
>
> - Règles opérationnelles (pour les agents) : `AGENTS.md` à la racine du dépôt.
> - Planning par étapes : `planning.md`.
>
> Version française de la spécification d'origine, avec corrections : `security-lab/` à la racine (§17, §20), HTMX marqué optionnel (§5), authentification/RBAC hors MVP (§12), phases adossées au planning de référence (§26).

## 1. Identité du projet

**Nom** : SecuMerge

SecuMerge est une **plateforme légère de gestion de findings de sécurité**, destinée à démontrer une pratique concrète du DevSecOps et de la sécurité applicative.

C'est un projet personnel indépendant, développé par un étudiant en cybersécurité et cloud.

L'objectif n'est **pas** de reproduire DefectDojo ni de construire une plateforme à l'échelle d'une entreprise.

L'objectif est de construire une **plateforme de sécurité petite, propre, fonctionnelle, documentée et démontrable**, capable de :

- recevoir des findings de sécurité provenant de différents scanners ;
- normaliser des findings hétérogènes dans un modèle commun ;
- dédupliquer les findings répétés ;
- stocker les findings et leur cycle de vie ;
- afficher les findings dans une interface web ;
- proposer filtrage et priorisation ;
- intégrer le scan de sécurité dans la CI/CD ;
- générer des rapports de sécurité utiles ;
- démontrer des concepts DevSecOps concrets.

## 2. Principe fondamental

Suivre :

> **PLAN → BUILD → TEST → DOCUMENT → COMMIT**

Ne pas implémenter de grosses fonctionnalités à l'aveugle.

Chaque fonctionnalité significative suit ce déroulé :

1. Comprendre le besoin.
2. Définir la plus petite implémentation utile.
3. L'implémenter.
4. La tester.
5. Mettre la documentation à jour.
6. Commiter.

Préférer de petits changements incrémentaux aux grandes réécritures.

## 3. Périmètre

### Dans le périmètre

SecuMerge doit fournir :

#### Ingestion des findings

Prendre en charge des findings de scanners externes.

Les premiers formats pris en charge :

- SARIF
- JSON

L'architecture doit permettre d'ajouter d'autres scanners/formats plus tard.

Scanners pressentis :

- Semgrep
- Trivy
- Checkov

Ces scanners sont des outils externes. SecuMerge ne doit **pas** tenter de les réimplémenter.

## 4. Architecture

Utiliser une architecture **monolithe modulaire**.

Architecture cible :

```text
                Scanners de sécurité externes
                         │
            ┌────────────┼────────────┐
            ↓            ↓            ↓
         Semgrep       Trivy       Checkov
            │            │            │
            └────────────┼────────────┘
                         ↓
                  SARIF / JSON
                         ↓
                Couche d'ingestion
                         ↓
                  Normalisation
                         ↓
                  Déduplication
                         ↓
                Cœur « findings »
                         ↓
                 Base PostgreSQL
                         ↓
                  API REST / UI
                         ↓
                Tableau de bord
```

CI/CD :

```text
Développeur
   ↓
Git push
   ↓
GitHub Actions
   ↓
Tests
   ↓
Scanners de sécurité
   ├── Semgrep
   ├── Trivy
   └── Checkov
   ↓
SARIF / JSON
   ↓
Ingestion SecuMerge
   ↓
Findings normalisés
   ↓
Tableau de bord / rapports
```

## 5. Stack technique

Utiliser la stack suivante sauf raison technique forte.

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

### Base de données

- PostgreSQL
- Utiliser JSONB là où c'est pertinent (données brutes de scanners, métadonnées flexibles). Ne pas en abuser quand un modèle relationnel convient mieux.

### Frontend

Frontend volontairement léger :

- Jinja2
- HTMX (optionnel, seulement si un besoin concret le justifie)
- HTML, CSS
- **Pas de React** sauf raison concrète.

Le projet doit rester facile à lancer localement.

### Infrastructure

- Docker
- Docker Compose

### CI/CD

- GitHub Actions

### Outils de sécurité

- Semgrep
- Trivy
- Checkov

### Tests

- pytest

## 6. Exigences fonctionnelles

### Finding

Un finding contient au minimum :

- id
- titre
- description
- sévérité
- statut
- scanner
- identifiant de règle/check
- fichier/ressource
- localisation quand disponible
- first_seen
- last_seen
- created_at
- updated_at
- fingerprint

Sévérités possibles :

- CRITICAL
- HIGH
- MEDIUM
- LOW
- INFO

Statuts possibles :

- OPEN
- CONFIRMED
- FALSE_POSITIVE
- ACCEPTED_RISK
- RESOLVED

Ne pas introduire d'états inutiles.

## 7. Normalisation des findings

Chaque scanner produit son propre schéma. Créer un modèle de finding interne commun.

Modèle conceptuel :

```text
Finding scanner
      ↓
Parser
      ↓
NormalizedFinding
      ↓
Validation
      ↓
Déduplication
      ↓
Base de données
```

Chaque parser de scanner doit être isolé :

```text
ingestion/
    parsers/
        sarif.py
        semgrep.py
        trivy.py
        checkov.py
```

Ne pas disséminer de logique spécifique à un scanner dans toute l'application.

## 8. Déduplication

La déduplication est une fonctionnalité importante.

Créer une empreinte déterministe à partir d'attributs stables. Entrées possibles :

- scanner
- identifiant de règle
- fichier/ressource
- localisation
- titre normalisé

L'algorithme exact doit être documenté.

Un même finding signalé à répétition par la CI/CD ne doit pas créer une quantité illimitée de doublons en base.

## 9. Cycle de vie d'un finding

Démontrer un cycle de vie de base :

```text
OPEN
  ↓
CONFIRMED
  ↓
RESOLVED
```

Chemins alternatifs :

```text
OPEN → FALSE_POSITIVE
OPEN → ACCEPTED_RISK
```

Stocker les horodatages des changements d'état significatifs.

Ne pas construire de moteur de workflow complexe.

## 10. Tableau de bord

Le tableau de bord doit fournir des informations utiles :

- total des findings
- findings ouverts
- findings CRITICAL / HIGH / MEDIUM / LOW
- findings par scanner
- findings par statut
- findings récents

Filtres :

- sévérité
- statut
- scanner
- date

L'UI privilégie l'utilisabilité et la clarté sur la complexité visuelle.

## 11. API

Exposer des endpoints REST pour les opérations de base :

```text
GET    /api/findings
GET    /api/findings/{id}
POST   /api/findings
POST   /api/import
PATCH  /api/findings/{id}
GET    /api/stats
```

Le nommage exact des endpoints peut être ajusté si l'architecture y gagne.

Utiliser des schémas Pydantic pour la validation des entrées/sorties de l'API.

## 12. Authentification

**Hors MVP** : à n'implémenter que si le temps le permet (durcissement, Phase 7). Ne pas construire de plateforme d'identité inutilement compliquée.

Si l'authentification est implémentée :

- les mots de passe ne sont jamais stockés en clair ;
- les secrets viennent de variables d'environnement ;
- la logique d'authentification est isolée ;
- l'autorisation est explicite.

Rôles possibles :

```text
ADMIN
ANALYST
VIEWER
```

N'implémenter le RBAC que s'il apporte une valeur réelle au projet.

## 13. Exigences de sécurité

La sécurité est au cœur du projet. L'application doit démontrer des pratiques de développement sûres.

### Secrets

Ne jamais commiter :

- mots de passe
- clés d'API
- tokens
- clés privées
- identifiants de base de données

Utiliser `.env` et `.env.example`. `.env` est ignoré par Git.

### Validation des entrées

Valider toute entrée externe. Utiliser Pydantic et une validation applicative appropriée.

Ne pas faire confiance aux fichiers de scanners importés.

### Uploads de fichiers

Si des rapports de scanners sont importés :

- valider le type de fichier ;
- imposer des limites de taille raisonnables ;
- parser prudemment ;
- rejeter les entrées malformées ;
- éviter l'exécution arbitraire de fichiers ;
- éviter la traversée de chemin (path traversal) ;
- ne jamais exécuter le contenu importé.

### Sécurité SQL

Utiliser des requêtes paramétrées via SQLAlchemy.

Ne jamais construire de requêtes SQL par concaténation de chaînes.

### Sécurité des dépendances

Scanner les dépendances. Garder un nombre minimal de dépendances.

### Sécurité des conteneurs

Utiliser :

- des images minimales quand c'est pratique ;
- un utilisateur non-root quand c'est pratique ;
- des versions épinglées quand c'est approprié ;
- le scan Trivy.

Ne pas ajouter de capacités Linux inutiles.

## 14. Pipeline DevSecOps

GitHub Actions doit démontrer un pipeline réaliste mais gérable.

Pipeline suggéré :

```text
1. Lint
      ↓
2. Tests unitaires
      ↓
3. Détection de secrets
      ↓
4. Scan des dépendances / paquets
      ↓
5. SAST
      ↓
6. Build du conteneur
      ↓
7. Scan du conteneur
      ↓
8. Scan IaC
      ↓
9. Tests d'intégration
```

Outils possibles :

- Ruff
- pytest
- Semgrep
- Trivy
- Checkov
- Gitleaks si pertinent

Ne pas ajouter d'outil juste pour augmenter le nombre d'outils. Chaque outil doit avoir un but documenté.

## 15. Philosophie CI/CD

Le pipeline doit échouer quand c'est justifié.

Ne pas créer de faux contrôles de sécurité qui passent toujours.

Pour chaque scanner :

1. Le lancer.
2. Capturer sa sortie.
3. Comprendre son code de retour.
4. Convertir/importer les findings quand c'est pertinent.
5. Documenter son rôle.

Le projet doit démontrer que les contrôles de sécurité impactent réellement le pipeline de développement.

## 16. Stratégie de tests

Utiliser pytest.

Les tests doivent couvrir :

### Tests unitaires

- parsers
- normalisation
- génération de fingerprint
- mapping de sévérité
- validation
- cycle de vie des findings

### Tests d'intégration

- interaction avec la base de données
- endpoints API
- ingestion des findings
- import de rapports de scanners

### Tests de sécurité

Tester au minimum :

- entrée malformée
- sévérité invalide
- upload surdimensionné
- opération non autorisée (là où l'authentification existe)
- findings en doublon
- formats de fichier invalides

Viser une couverture pertinente plutôt qu'un pourcentage arbitraire.

## 17. Labo de démonstration / sécurité

Créer un labo de sécurité local reproductible avec des exemples volontairement vulnérables que les scanners peuvent détecter :

```text
security-lab/
```

Vulnérabilités possibles :

- motif de code non sûr pour Semgrep ;
- dépendance vulnérable pour Trivy ;
- configuration Docker non sûre ;
- exemple Terraform/IaC volontairement non sûr pour Checkov.

**Important** : ces exemples vulnérables restent isolés de l'application de production.

Ne jamais introduire volontairement de vulnérabilité dans le vrai backend SecuMerge pour la démonstration.

## 18. Documentation

La documentation est un livrable de premier ordre.

Créer :

```text
README.md
docs/
    architecture.md
    setup.md
    development.md
    security.md
    scanners.md
    ci-cd.md
    testing.md
    demo.md
```

Le README doit expliquer :

1. Ce qu'est SecuMerge.
2. Pourquoi il existe.
3. L'architecture.
4. Les technologies.
5. Comment le lancer.
6. Comment lancer les tests.
7. Comment lancer les scanners.
8. Comment les findings sont importés.
9. Comment fonctionne la CI/CD.
10. Les considérations de sécurité.
11. Les limites connues.
12. Les améliorations futures.

## 19. Documentation d'architecture

Documenter les décisions d'architecture importantes. Pour chaque décision importante, expliquer :

- problème
- alternatives
- solution retenue
- raison
- compromis

Exemple :

```text
Décision :
Utiliser un monolithe modulaire plutôt que des microservices.

Raison :
Le projet vise à démontrer l'ingénierie sécurité,
pas la complexité des systèmes distribués.

Compromis :
Moins de scalabilité indépendante, mais développement,
tests et déploiement nettement plus simples.
```

Ne pas introduire de microservices simplement parce que cela impressionne.

## 20. Structure du projet

Viser une structure similaire à :

```text
secumerge/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── ingestion/
│   │   └── parsers/
│   ├── repositories/
│   └── templates/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── security/
│
├── security-lab/
│
├── docs/
│
├── .github/
│   └── workflows/
│
├── alembic/
│
├── docker/
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── AGENTS.md
```

Cette structure peut évoluer si l'implémentation révèle une meilleure organisation.

Ne pas forcer la structure si elle crée de la complexité inutile.

## 21. Règles de développement

### Règle 1 — Inspecter avant de changer

Avant de modifier du code :

- inspecter le dépôt ;
- comprendre l'architecture existante ;
- identifier les dépendances ;
- vérifier les tests existants ;
- vérifier `git status`.

Ne jamais écraser aveuglément du travail existant.

### Règle 2 — Petites tranches

Implémenter une fonctionnalité cohérente à la fois.

Mauvais :

> Construire toute la plateforme.

Bon :

> Implémenter le parser SARIF + tests.

Puis :

> Implémenter le modèle finding + migration.

Puis :

> Implémenter le service d'ingestion.

Puis :

> Implémenter le tableau de bord.

### Règle 3 — Pas de dépendance inutile

Avant d'ajouter une dépendance, se demander :

> Cette dépendance est-elle réellement nécessaire ?

Préférer la bibliothèque standard Python ou les dépendances existantes quand c'est raisonnable.

### Règle 4 — Pas d'architecture prématurée

Ne pas introduire :

- Kubernetes
- Kafka
- Redis
- Celery
- Elasticsearch
- microservices
- bus d'événements

sauf si un vrai besoin du projet le justifie.

Le but est un projet d'ingénierie solide, pas une collection de technologies.

## 22. Règles Git

Utiliser des commits explicites :

```text
feat: add finding domain model
feat: implement SARIF parser
feat: add finding ingestion API
test: add SARIF parser tests
security: add container scanning
ci: add security pipeline
docs: document ingestion architecture
fix: prevent duplicate findings
```

Ne jamais faire de commit géant contenant des changements sans rapport.

## 23. Ce qu'il ne faut PAS construire

Ne PAS transformer SecuMerge en :

- clone de DefectDojo ;
- SIEM ;
- SOC ;
- scanner de vulnérabilités ;
- SOAR complet ;
- chatbot IA ;
- plateforme de microservices ;
- plateforme IAM d'entreprise.

La plateforme consomme et gère les findings de scanners.

Sa valeur est :

> **Normalisation + agrégation + cycle de vie + visibilité + intégration DevSecOps**

## 24. IA

L'IA n'est PAS une fonctionnalité obligatoire du MVP.

Ne pas ajouter de chatbot IA simplement parce que « l'IA » impressionne.

Si l'IA est introduite plus tard, elle doit résoudre un problème concret :

- résumé de finding ;
- aide à la priorisation ;
- analyse de similarité des doublons ;
- explication de remédiation.

L'IA ne doit jamais prendre silencieusement de décisions de sécurité critiques.

Les recommandations générées par IA doivent être clairement identifiées.

## 25. Definition of Done

Une fonctionnalité n'est PAS terminée tant que :

- l'implémentation fonctionne ;
- les tests existent ;
- les considérations de sécurité sont traitées ;
- la documentation est mise à jour ;
- l'exécution locale fonctionne ;
- `git status` est propre ;
- le commit est explicite.

## 26. Phases de développement

> Le planning de référence est `planning.md` (Étapes 0 à 12). Les phases ci-dessous décrivent la même progression par grands blocs fonctionnels ; en cas d'écart, c'est `planning.md` qui fait foi.

### Phase 0 — Fondations

- initialisation du dépôt ;
- environnement Python ;
- squelette FastAPI ;
- PostgreSQL ;
- Docker Compose ;
- gestion de la configuration ;
- endpoint de health ;
- tests de base ;
- README.

### Phase 1 — Domaine Finding

- modèles de base de données ;
- migrations ;
- schéma de finding ;
- sévérité ;
- statut ;
- fingerprint.

### Phase 2 — Ingestion

- parser SARIF ;
- ingestion JSON ;
- validation ;
- normalisation ;
- déduplication.

### Phase 3 — API

- endpoints findings ;
- endpoint d'import ;
- filtrage ;
- pagination ;
- statistiques.

### Phase 4 — Tableau de bord web

- tableau de bord ;
- liste des findings ;
- détail d'un finding ;
- filtres ;
- mise à jour de statut.

### Phase 5 — Scanners de sécurité

Intégrer :

- Semgrep
- Trivy
- Checkov

Générer de vrais rapports et les importer dans SecuMerge.

### Phase 6 — CI/CD DevSecOps

Implémenter GitHub Actions :

- lint ;
- tests ;
- détection de secrets ;
- SAST ;
- scan des dépendances ;
- scan du conteneur ;
- scan IaC ;
- tests d'intégration.

### Phase 7 — Durcissement sécurité

Revoir :

- authentification ;
- autorisation ;
- validation des entrées ;
- sécurité des uploads ;
- secrets ;
- conteneurs ;
- dépendances ;
- sécurité de l'API.

### Phase 8 — Labo de sécurité et démonstration

Créer une démonstration reproductible :

```text
Code / infrastructure vulnérables
             ↓
         Git push
             ↓
      CI de sécurité
             ↓
     Findings des scanners
             ↓
      Import SecuMerge
             ↓
        Déduplication
             ↓
        Tableau de bord
             ↓
     Cycle de vie finding
```

### Phase 9 — Documentation et portfolio

Finaliser :

- README ;
- schéma d'architecture ;
- captures d'écran ;
- instructions de démonstration ;
- analyse de sécurité ;
- limites ;
- travaux futurs ;
- rapport technique.

## 27. Ordre de priorité

Si le temps devient limité, prioriser :

1. Modèle de finding de base
2. Ingestion SARIF
3. Normalisation
4. Déduplication
5. API
6. Tableau de bord
7. Intégration des scanners
8. CI/CD
9. Durcissement sécurité
10. Documentation
11. Améliorations optionnelles

Ne jamais sacrifier le système de base fonctionnel pour des fonctionnalités optionnelles.

## 28. Objectif final

À la fin, SecuMerge doit permettre de démontrer en entretien :

> « J'ai conçu et implémenté une plateforme légère de gestion de findings de sécurité. Elle consomme les résultats d'outils comme Semgrep, Trivy et Checkov, les normalise et les déduplique, stocke leur cycle de vie dans PostgreSQL, les expose via une API et un tableau de bord, et intègre les contrôles de sécurité dans GitHub Actions. »

Le projet doit être :

- fonctionnel
- sûr
- testable
- reproductible
- documenté
- compréhensible
- démontrable
- prêt pour GitHub

La qualité de l'ingénierie compte plus que le nombre de technologies utilisées.
