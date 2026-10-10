# Scanners

SecuMerge ne réimplémente aucun scanner : il **consomme** leurs rapports.

| Scanner | Type | Cible | Sortie |
|---|---|---|---|
| **Semgrep** | SAST | code (Python) | SARIF 2.1.0 |
| **Trivy** | SCA / conteneurs | dépendances (`requirements.txt`, images) | SARIF 2.1.0 |
| **Checkov** | IaC | Terraform, Dockerfile, docker-compose | SARIF 2.1.0 |

Les trois parlent SARIF 2.1.0 : le cœur de parsing est mutualisé dans
`app/ingestion/sarif.py`, chaque scanner garde un module dédié dans
`app/ingestion/parsers/`.

## Comment ils sont lancés

- **CI (GitHub Actions)** : images Docker officielles sur le **code du dépôt**,
  en excluant `security-lab/` :

  | Scanner | Commande | Exclusions |
  |---|---|---|
  | Semgrep | `semgrep scan --config p/default` (règles du registre) | `--exclude security-lab` |
  | Trivy | `trivy fs --scanners vuln` | `--skip-dirs security-lab` |
  | Checkov | `checkov --directory /src` | `--skip-path security-lab` |

- **Test Lab (local)** : `security-lab/run-lab.ps1` lance les mêmes images sur
  les cibles volontairement vulnérables de `security-lab/`, avec des **règles
  Semgrep locales** (`semgrep-rules.yml`) pour un scan déterministe.

## Ce qui est extrait d'un rapport

| Champ SecuMerge | Source SARIF |
|---|---|
| `rule_id` | `results[].ruleId` |
| `title` | `rules[].shortDescription` sinon la première ligne du message |
| `description` | `results[].message.text` |
| sévérité | `security-severity` (CVSS) sinon `level` (voir mapping) |
| `cvss_score` | `rules[].properties.security-severity` |
| `cwe` | `rules[].properties.tags` (motif `CWE-<nombre>`) |
| `confidence` | `rules[].properties.confidence` |
| `file_path` | `locations[0].physicalLocation.artifactLocation.uri` (slashs normalisés) |
| `location` | `region.startLine` et `startColumn` → `« ligne:colonne »` |

## Mapping des sévérités

1. **Si un CVSS est fourni** (`security-severity`) :
   `≥ 9` → `CRITICAL`, `≥ 7` → `HIGH`, `≥ 4` → `MEDIUM`, `> 0` → `LOW`, `0` → `INFO`.
2. **Sinon, le niveau SARIF** : `error` → `HIGH`, `warning` → `MEDIUM`,
   `note` → `LOW`, `none`/absent → `INFO`.

Le CVSS sert ensuite au **score de risque** (voir README) : un CVE `CRITICAL`
avec CVSS 9.8 obtient `(90 + 98) / 2 = 94`.

## Empreinte (déduplication)

`sha256(scanner | rule_id | fichier | « ligne:colonne »)` — le titre n'en fait
pas partie (il peut être reformulé). Deux scans successifs du même problème
produisent la même empreinte : pas de doublon, `last_seen` mis à jour, une
occurrence ajoutée.

## Ajouter un scanner

Voir [development.md](development.md#ajouter-un-parseur-de-scanner). Pour un
scanner qui produit du SARIF standard, c'est une vingtaine de lignes, plus les
tests et un échantillon dans `tests/data/`.
