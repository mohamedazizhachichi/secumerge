<#
    Test Lab SecuMerge : verification du pipeline de bout en bout.

    Lance Semgrep, Trivy et Checkov (images Docker officielles) sur les
    cibles volontairement vulnerables de security-lab\, envoie les rapports
    a POST /scans, puis verifie que le Security Gate repond PASS.

    Prerequis :
      - Docker Desktop demarre ;
      - stack SecuMerge lance : docker compose up -d (a la racine du depot).

    Premier lancement : telechargement des images (~600 Mo) et de la base
    de vulnerabilites Trivy ; les suivants sont rapides.
#>
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Project = "security-lab",
    [string]$Repository = "vulnerable-app",
    [string]$CommitSha = ("lab-" + (Get-Date -Format "yyyyMMddHHmmss"))
)

$ErrorActionPreference = "Stop"

$labDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $labDir
$outDir = Join-Path $labDir "out"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Fail([string]$message) {
    Write-Host "`nERREUR : $message" -ForegroundColor Red
    exit 1
}

# --------------------------------------------------------------- 0. API
Write-Host "Verification de l'API $BaseUrl ..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5
    if ($health.status -ne "ok") { Fail "l'API repond mais pas 'ok'." }
} catch {
    Fail "l'API ne repond pas. Lance d'abord : docker compose up -d"
}
Write-Host "API OK - commit de test : $CommitSha"

# ----------------------------------------------------------- 1. scanners
Write-Host "`n[1/4] Semgrep (analyse statique Python) ..." -ForegroundColor Cyan
docker run --rm -v "${repoRoot}:/src" semgrep/semgrep `
    semgrep scan --config /src/security-lab/semgrep-rules.yml `
    --sarif --output /src/security-lab/out/semgrep.sarif `
    --metrics off --quiet /src/security-lab/vulnerable-app
if ($LASTEXITCODE -ne 0) { Fail "Semgrep a echoue (code $LASTEXITCODE)." }

Write-Host "[2/4] Trivy (dependances vulnerables) ..." -ForegroundColor Cyan
docker run --rm -v "${repoRoot}:/src" -v "${outDir}/trivy-cache:/root/.cache/trivy" `
    aquasec/trivy fs --scanners vuln --format sarif `
    --output /src/security-lab/out/trivy.sarif --quiet `
    /src/security-lab/vulnerable-app
if ($LASTEXITCODE -ne 0) {
    Write-Host "  base de vulnerabilites injoignable, repli sur le cache local..." -ForegroundColor Yellow
    docker run --rm -v "${repoRoot}:/src" -v "${outDir}/trivy-cache:/root/.cache/trivy" `
        aquasec/trivy fs --scanners vuln --skip-db-update --format sarif `
        --output /src/security-lab/out/trivy.sarif --quiet `
        /src/security-lab/vulnerable-app
    if ($LASTEXITCODE -ne 0) { Fail "Trivy a echoue (code $LASTEXITCODE)." }
}

Write-Host "[3/4] Checkov (infrastructure as code) ..." -ForegroundColor Cyan
docker run --rm -v "${repoRoot}:/src" bridgecrew/checkov `
    --directory /src/security-lab/infra `
    --output sarif --output-file-path /src/security-lab/out `
    --soft-fail --quiet
if ($LASTEXITCODE -ne 0) { Fail "Checkov a echoue (code $LASTEXITCODE)." }
$checkovGenerated = Join-Path $outDir "results_sarif.sarif"
$checkovReport = Join-Path $outDir "checkov.sarif"
if (Test-Path $checkovGenerated) { Move-Item -Force $checkovGenerated $checkovReport }
if (-not (Test-Path $checkovReport)) { Fail "Checkov n'a pas produit de rapport SARIF." }

# -------------------------------------------------------------- 2. envoi
Write-Host "`n[4/4] Envoi des rapports a POST /scans ..." -ForegroundColor Cyan
$summary = @()
Push-Location $outDir
try {
    foreach ($scanner in @("semgrep", "trivy", "checkov")) {
        $report = "$scanner.sarif"
        if (-not (Test-Path $report)) { Fail "rapport manquant : $report" }

        $raw = curl.exe -s -X POST "$BaseUrl/scans" `
            -F "file=@$report" `
            -F "project=$Project" -F "repository=$Repository" `
            -F "scanner=$scanner" -F "commit_sha=$CommitSha" `
            -F "branch=lab" -F "is_complete=true"
        if (-not $raw) { Fail "reponse vide de l'API pour $scanner." }

        $json = $raw | ConvertFrom-Json
        if (-not $json.id) { Fail "envoi $scanner refuse : $raw" }

        $found = [int]$json.findings_created + [int]$json.findings_updated
        if ($found -eq 0) { Fail "$scanner n'a produit aucun finding." }

        $summary += [pscustomobject]@{
            Scanner  = $scanner
            ScanId   = $json.id
            Nouveaux = $json.findings_created
            MisAJour = $json.findings_updated
            Resolus  = $json.findings_resolved
        }
        Write-Host ("  {0} : scan #{1} ({2} nouveaux, {3} mis a jour)" -f `
            $scanner, $json.id, $json.findings_created, $json.findings_updated)
    }
} finally {
    Pop-Location
}

# --------------------------------------------------------------- 3. gate
$gate = Invoke-RestMethod -Uri "$BaseUrl/gate?project=$Project&repository=$Repository&commit_sha=$CommitSha"
if ($gate.status -ne "PASS") {
    $missingList = $gate.missing -join ", "
    Fail ("Security Gate en echec : {0} (manquants : {1})" -f $gate.status, $missingList)
}

Write-Host ""
$summary | Format-Table -AutoSize
Write-Host "Pipeline complet OK : gate PASS pour $CommitSha" -ForegroundColor Green
Write-Host "Tableau de bord : $BaseUrl/"
