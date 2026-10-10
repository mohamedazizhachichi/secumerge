# Security Lab

Cibles **volontairement vulnérables** et script de vérification du pipeline
complet. Rien ici n'est destiné à la production : ces fichiers existent pour
que Semgrep, Trivy et Checkov détectent de vrais problèmes, que SecuMerge les
ingère, calcule les scores et que le Security Gate réponde PASS.

| Fichier | Cible du scanner | Exemples de problèmes |
|---|---|---|
| `vulnerable-app/app.py` | Semgrep (règles locales) | `eval()`, `shell=True`, secrets en dur, `yaml.load()` |
| `vulnerable-app/requirements.txt` | Trivy | CVE connues (PyYAML 5.3.1, requests 2.19.0, Jinja2 2.10) |
| `infra/main.tf` | Checkov | bucket S3 public, non chiffré, SSH ouvert au monde |

## Lancer le labo

```powershell
# Prérequis : Docker Desktop démarré et le stack lancé
docker compose up -d

# À la racine du dépôt
.\security-lab\run-lab.ps1
```

Le script :

1. vérifie que l'API répond (`/health`) ;
2. lance les trois scanners via leurs images Docker officielles
   (`semgrep/semgrep`, `aquasec/trivy`, `bridgecrew/checkov`) ;
3. envoie les rapports SARIF à `POST /scans` avec un commit de test ;
4. vérifie que chaque scanner a créé/mis à jour des findings ;
5. vérifie que `GET /gate` répond **PASS** ;
6. affiche un récapitulatif et sort en erreur (code 1) si un maillon casse.

Les rapports et le cache Trivy atterrissent dans `security-lab/out/`
(ignoré par git). Le premier lancement télécharge les images (~600 Mo) et la
base de vulnérabilités Trivy ; c'est rapide ensuite.

> Rejouer le script ne crée pas de doublons : les findings sont dédupliqués
> par empreinte stable, seuls `last_seen` et les occurrences évoluent.
