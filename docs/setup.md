# Installation

## Prérequis

- **Docker Desktop** installé et démarré (Windows, macOS ou Linux) ;
- **Git** ;
- port **8000** libre ;
- optionnel : Python 3.13 pour le lint local (`ruff check .`).

## Installation pas à pas

```powershell
git clone https://github.com/mohamedazizhachichi/secumerge.git
cd secumerge
Copy-Item .env.example .env
docker compose up --build
```

Le premier démarrage construit l'image et télécharge PostgreSQL 17. Ensuite,
dans un second terminal :

```powershell
# Créer le schéma (les 6 tables + alembic_version)
docker compose exec api alembic upgrade head

# Vérifier
docker compose exec api pytest
docker compose exec api alembic check
```

## Vérifier que tout répond

| URL | Attendu |
|---|---|
| http://localhost:8000/health | `{"status":"ok"}` |
| http://localhost:8000/docs | la documentation interactive de l'API |
| http://localhost:8000/ | le tableau de bord (vide au début) |

## Premier rapport de scan

```powershell
curl.exe -X POST http://localhost:8000/scans `
  -F "file=@tests/data/semgrep-example.sarif" `
  -F "project=demo" -F "repository=app-vulnerable" `
  -F "scanner=semgrep" -F "commit_sha=abc123" -F "branch=main"
```

Recharge http://localhost:8000/ : un finding `MEDIUM` doit apparaître avec son
score.

## Test Lab (démonstration complète)

```powershell
.\security-lab\run-lab.ps1
```

Prérequis : Docker Desktop démarré et le stack lancé. Le premier lancement
télécharge les images des scanners (~600 Mo) et la base de vulnérabilités Trivy
(plusieurs minutes) ; les suivants sont rapides.

## Arrêter / repartir

```powershell
docker compose down          # arrêter (les données restent dans le volume)
docker compose down -v       # arrêter et SUPPRIMER la base
docker compose up -d         # redémarrer
```

## Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| « Copiez .env.example vers .env avant de lancer » | Le fichier `.env` n'existe pas : `Copy-Item .env.example .env` |
| Port 8000 déjà utilisé | Un autre service occupe le port : `Get-NetTCPConnection -LocalPort 8000 -State Listen` puis arrêtez-le |
| `alembic upgrade head` échoue | Le conteneur `db` n'est pas prêt : attendez `healthy` dans `docker compose ps` |
| Trivy ne peut pas télécharger sa base | Réseau vers le miroir indisponible : le Test Lab réessaie automatiquement avec `--skip-db-update` (cache local) |
| PowerShell refuse un script `.ps1` | Exécution bloquée par la politique : `powershell -ExecutionPolicy Bypass -File .\security-lab\run-lab.ps1` |
| Les scripts `.ps1` du projet ne doivent pas contenir d'accents | Windows PowerShell 5.1 lit l'UTF-8 sans BOM en ANSI : garder **ASCII + CRLF** (règle du projet) |
