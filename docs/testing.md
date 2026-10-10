# Tests

## Lancer les tests

```powershell
docker compose exec api pytest
```

Attendu : **48 tests** verts.

## Organisation

| Fichier | Type | Ce qui est couvert |
|---|---|---|
| `tests/test_health.py` | API | `/health` |
| `tests/test_models.py` | Unitaire | les 6 tables sont enregistrées |
| `tests/test_ingestion.py` | Unitaire | empreinte, mapping de sévérité, extraction CVSS/CWE/confiance, parsing des 3 scanners, tolérance aux rapports malformés |
| `tests/test_risk.py` | Unitaire | formule du score (barème, CVSS, confiance, bornes) |
| `tests/test_scans.py` | Intégration | validation des uploads (taille, JSON, scanner), création/mise à jour des findings, occurrences, résolution sur scan complet, évaluations de risque |
| `tests/test_gate.py` | Intégration | PASS/FAIL, scan partiel, dépôt inconnu (fail-closed), mélange complet/partiel |
| `tests/test_ui.py` | Intégration | rendu du dashboard, filtres sévérité/statut/scanner, compteurs |

Les échantillons SARIF vivent dans `tests/data/` (rapports Semgrep, Trivy,
Checkov, rapports vides/invalides, deux findings pour la disparition).

## Comment les tests d'intégration isolent la base

`tests/conftest.py` ouvre **une connexion avec transaction externe** et fournit :

- `client` : un `TestClient` dont la dépendance `get_db` renvoie des sessions
  liées à cette transaction ;
- `db_session` : une session pour les assertions.

Tout ce que le test insère est **annulé en fin de test** : la base de
développement n'est jamais polluée, et les tests peuvent coexister avec les
données de démonstration (les assertions ciblent des noms uniques).

## Stratégie

- **Unitaire d'abord** : ce qui est pur (empreinte, mappings, formule, parsing)
  se teste sans base et couvre les cas limites.
- **Intégration ciblée** : les comportements qui comptent — déduplication,
  résolution, gate — passent par l'API réelle et la vraie base.
- **Sécurité en priorité** : taille/lisibilité des uploads, JSON invalide,
  scanner inconnu, fail-closed.
- La CI rejoue ces tests à chaque push (voir [ci-cd.md](ci-cd.md)).

## Ajouter un test

1. Choisir le fichier selon la nature (unitaire vs intégration) ;
2. pour une intégration, utiliser les fixtures `client` et `db_session` et des
   noms uniques (`projet`/`dépôt` de test) pour éviter les collisions avec les
   données existantes ;
3. lancer `docker compose exec api pytest` — les modules sont montés dans le
   conteneur, aucun rebuild n'est nécessaire.
