# Développement

## Organisation du dépôt

```text
secumerge/
├── app/
│   ├── main.py              # application FastAPI
│   ├── api/                 # routes : scans.py, gate.py, ui.py
│   ├── core/                # configuration + connexion base
│   ├── models/              # modèles SQLAlchemy (6 tables)
│   ├── ingestion/           # parsers SARIF + empreinte
│   │   └── parsers/         # semgrep.py, trivy.py, checkov.py
│   ├── schemas/             # contrats Pydantic
│   ├── services/            # logique métier (scans, risk, gate, dashboard)
│   └── templates/           # page Jinja2
├── alembic/                 # migrations
├── security-lab/            # cibles vulnérables + script de démo
├── tests/                   # pytest + échantillons SARIF
├── docs/                    # cette documentation
└── .github/workflows/       # CI/CD
```

## Principes (résumé de `AGENTS.md`)

**PLAN → BUILD → TEST → DOCUMENT → COMMIT.**

1. Inspecter avant de modifier (architecture, tests, `git status`).
2. La plus petite tranche utile — jamais « tout construire d'un coup ».
3. Tester dans le même changement.
4. Documenter dans le même changement.
5. Commiter par petits pas thématiques (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `security:`).

Pas de nouvelle dépendance sans nécessité ; interdits sauf besoin réel :
Kubernetes, Kafka, Redis, Celery, Elasticsearch, microservices, IA.

## Commandes utiles

```powershell
docker compose up -d --build                     # (re)construire et lancer
docker compose exec api pytest                   # tests
docker compose exec api alembic upgrade head     # migrations
docker compose exec api alembic check            # modèles <-> migrations synchronisés ?
ruff check .                                     # lint
.\security-lab\run-lab.ps1                       # démo de bout en bout
```

## Ajouter un parseur de scanner

1. **Créer le module** `app/ingestion/parsers/monscanner.py` — s'il produit du
   SARIF, il suffit de déléguer au cœur commun :

   ```python
   from app.ingestion.sarif import parse_sarif_results

   SCANNER = "monscanner"

   def parse_monscanner_report(report):
       return parse_sarif_results(report, SCANNER)
   ```

   Sinon, produire des `NormalizedFinding` (voir `app/ingestion/models.py`).

2. **Enregistrer le scanner** dans `app/ingestion/parsers/__init__.py`
   (`PARSERS`) et dans l'énumération `Scanner` (`app/models/enums.py`).

3. **Ajouter un échantillon** dans `tests/data/` et des tests unitaires dans
   `tests/test_ingestion.py` (parsing + extraction CVSS/CWE/confiance).

4. **Vérifier l'intégration** : un test dans `tests/test_scans.py` qui poste le
   rapport et vérifie le finding créé.

## Ajouter une migration

1. Modifier ou créer un modèle dans `app/models/`.
2. Générer la migration :

   ```powershell
   docker compose exec api alembic revision --autogenerate -m "description courte"
   ```

3. Relire le fichier généré dans `alembic/versions/` (nommage, `ondelete`, etc.).
4. Appliquer et vérifier :

   ```powershell
   docker compose exec api alembic upgrade head
   docker compose exec api alembic check   # doit répondre « No new upgrade operations detected »
   ```

La convention de nommage des contraintes vit dans `app/core/database.py` ; les
migrations écrites à la main doivent la respecter.

## Conventions

- Code et identifiants en anglais ; commentaires et documentation en français.
- Les scripts `.ps1` restent en **ASCII avec fins de ligne CRLF** (Windows
  PowerShell 5.1 lit l'UTF-8 sans BOM en ANSI — leçon apprise).
- Les tests d'intégration utilisent la fixture `client` (`tests/conftest.py`) :
  chaque test tourne dans une transaction annulée à la fin, la base de
  développement n'est jamais polluée.
- Le rapport d'un scanner est une **donnée non fiable** : les parseurs ignorent
  les entrées malformées au lieu d'échouer.

## Reprendre le projet

Le planning initial est dans `docs/planning.md` (étapes 0 à 12) ; la
spécification complète dans `docs/spec-secumerge.md`. Les limites connues et la
suite (durcissement) sont dans `docs/security.md`.
