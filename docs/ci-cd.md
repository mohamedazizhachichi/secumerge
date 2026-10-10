# CI/CD (GitHub Actions)

Le workflow [`.github/workflows/security.yml`](../.github/workflows/security.yml)
s'exécute sur chaque **push vers `main`** et sur chaque **pull request**.

[![security](https://github.com/mohamedazizhachichi/secumerge/actions/workflows/security.yml/badge.svg)](https://github.com/mohamedazizhachichi/secumerge/actions/workflows/security.yml)

## Les étapes

| # | Étape | Détail |
|---|---|---|
| 1 | Checkout | `actions/checkout@v4` |
| 2 | `.env` | `cp .env.example .env` (le compose l'exige) |
| 3 | Stack | `docker compose up -d --build` (api + postgres) |
| 4 | Attente | boucle sur `GET /health` (max 60 s) |
| 5 | Migrations | `docker compose exec -T api alembic upgrade head` |
| 6 | Tests | `docker compose exec -T api pytest` |
| 7 | Cache Trivy | `actions/cache` sur `~/.cache/trivy` (base partagée entre les runs) |
| 8 | Semgrep | `p/default` sur le dépôt, hors `security-lab/` |
| 9 | Trivy | `fs --scanners vuln`, hors `security-lab/` |
| 10 | Checkov | Dockerfile / compose, hors `security-lab/` |
| 11 | Ingestion | les 3 SARIF → `POST /scans` (commit = `github.sha`) |
| 12 | **Gate** | `jq -e '.status == "PASS"'` — l'étape qui **fait échouer le job** |
| 13 | Artefacts | rapports SARIF téléchargeables (`if: always()`) |
| 14 | Debug | logs du stack si échec (`if: failure()`) |

## Ce que la CI garantit

- **Les tests passent** — sinon le job s'arrête avant les scans.
- **Les trois scanners ont réellement tourné et produit un scan complet** —
  sinon le Security Gate répond `FAIL` et le job échoue.
- **Les rapports sont publiés** en artefact (utile pour diagnostiquer un échec).
- La base Trivy est mise en cache : les runs suivants sont plus rapides
  (premier run observé : ~1 min 30 ; la base se télécharge en parallèle).

## Ce que la CI ne fait pas (encore)

- Échouer sur la **criticité** des findings (le gate vérifie la présence des
  scanners, pas les scores) ;
- scanner l'**image** SecuMerge (build + Trivy image) ;
- la détection de **secrets** (Gitleaks) ;
- le lint (`ruff`) et les tests de sécurité dédiés.

Voir [security.md](security.md#limites-connues) pour la suite planifiée.

## Bloquer les merges (protection de branche)

Pour que le gate bloque réellement les fusions (et pas seulement la CI) :

1. GitHub → le dépôt → **Settings** → **Branches** ;
2. **Add branch protection rule** ;
3. Branch name pattern : `main` ;
4. cocher **Require status checks to pass before merging** ;
5. chercher et sélectionner le check **pipeline** (workflow « security ») ;
6. enregistrer.

À partir de là, une pull request dont le job `pipeline` échoue ne peut plus
être fusionnée.

## Lancer la CI sur un fork ou en local

Le workflow n'utilise que Docker et bash : toutes ses commandes peuvent être
rejouées à la main. Le Test Lab (`security-lab/run-lab.ps1`) couvre localement
le même parcours — scanners → ingestion → gate — avec des cibles dédiées.
