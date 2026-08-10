param(
  [Parameter(Mandatory=$true)][string]$MasterPath,
  [string]$Branch = "agent/preset02-p01-binary-ingress",
  [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\.."),
  [string]$GameRepoRoot = ""
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$ExpectedSha = "ce76243a4b89147a4900e823041b5392e2b19b13549aaa9fcd95cbf3e34d3fe3"
$ExpectedBytes = 747624
$Canonical = Join-Path $RepoRoot "production\first_playable\training_rival\source\training_rival_master.png"
$Lot = Join-Path $RepoRoot "production\first_playable\training_rival\first_playable_lot_01"
$Animations = Join-Path $Lot "animations"
$Staging = Join-Path $Lot "__p01_ingress_staging"
$SourceValidator = Join-Path $RepoRoot "tools\validate_training_rival_source_intake.py"
$P01Validator = Join-Path $RepoRoot "tools\validate_training_rival_p01.py"
$GlobalValidator = Join-Path $RepoRoot "tools\validate_first_playable_art_production.py"

function Require-CleanRepo {
  $dirty = @(git status --porcelain)
  if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_status_failed" }
  if ($dirty.Count -gt 0) {
    $dirty | ForEach-Object { Write-Host "PRESET02_DIRTY=$_" }
    throw "PRESET02_INGRESS=BLOCKED working_tree_not_clean"
  }
}

function Resolve-Python {
  foreach ($candidate in @("py", "python", "python3")) {
    try {
      Get-Command $candidate -ErrorAction Stop | Out-Null
      return $candidate
    } catch {}
  }
  throw "PRESET02_INGRESS=BLOCKED python_missing"
}

function Run-Python([string]$Python, [string[]]$Args) {
  if ($Python -eq "py") { & py -3 @Args }
  else { & $Python @Args }
  if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED python_exit=$LASTEXITCODE args=$($Args -join ' ')" }
}

$MasterPath = (Resolve-Path $MasterPath).Path
if (-not (Test-Path $MasterPath -PathType Leaf)) { throw "PRESET02_INGRESS=BLOCKED master_missing" }
$actualBytes = (Get-Item $MasterPath).Length
$actualSha = (Get-FileHash $MasterPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "PRESET02_MASTER_BYTES=$actualBytes"
Write-Host "PRESET02_MASTER_SHA256=$actualSha"
if ($actualBytes -ne $ExpectedBytes) { throw "PRESET02_INGRESS=BLOCKED byte_count_mismatch expected=$ExpectedBytes" }
if ($actualSha -ne $ExpectedSha) { throw "PRESET02_INGRESS=BLOCKED sha256_mismatch expected=$ExpectedSha" }
Write-Host "PRESET02_EXACT_BINARY=PASS"

foreach ($required in @($SourceValidator, $P01Validator, $GlobalValidator)) {
  if (-not (Test-Path $required)) { throw "PRESET02_INGRESS=BLOCKED missing_required_file=$required" }
}
Require-CleanRepo

Write-Host "PRESET02_MAIN_SYNC=BEGIN"
git fetch origin
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_fetch" }
git switch main
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_switch_main" }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_pull_main" }
Require-CleanRepo
Write-Host "PRESET02_MAIN_SYNC=PASS"

$existing = git show-ref --verify --quiet "refs/heads/$Branch"
if ($LASTEXITCODE -eq 0) { throw "PRESET02_INGRESS=BLOCKED local_branch_exists=$Branch" }
git switch -c $Branch origin/main
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED branch_create" }
Write-Host "PRESET02_BRANCH=PASS name=$Branch"

New-Item -ItemType Directory -Force -Path (Split-Path $Canonical -Parent) | Out-Null
Copy-Item $MasterPath $Canonical -Force
$canonicalSha = (Get-FileHash $Canonical -Algorithm SHA256).Hash.ToLowerInvariant()
if ($canonicalSha -ne $ExpectedSha) { throw "PRESET02_INGRESS=BLOCKED post_copy_sha256_mismatch" }
Write-Host "PRESET02_CANONICAL_MASTER_COPY=PASS"

$python = Resolve-Python
Run-Python $python @($SourceValidator)
Write-Host "PRESET02_SOURCE_INTAKE_LOCAL=PASS"

if (-not $GameRepoRoot) {
  $candidateGameRepo = Join-Path (Split-Path $RepoRoot -Parent) "taijifu-masters"
  if (Test-Path (Join-Path $candidateGameRepo "tools\materialize_training_rival_p01.py")) {
    $GameRepoRoot = $candidateGameRepo
  }
}

$tempGenerator = $null
if ($GameRepoRoot -and (Test-Path (Join-Path $GameRepoRoot "tools\materialize_training_rival_p01.py"))) {
  $generator = Join-Path $GameRepoRoot "tools\materialize_training_rival_p01.py"
  Write-Host "PRESET02_GENERATOR_SOURCE=sibling_repo"
} else {
  $tempGenerator = Join-Path ([System.IO.Path]::GetTempPath()) "taijifu_materialize_training_rival_p01.py"
  $raw = "https://raw.githubusercontent.com/Tehkne-Solutions/taijifu-masters/main/tools/materialize_training_rival_p01.py"
  Invoke-WebRequest -UseBasicParsing -Uri $raw -OutFile $tempGenerator
  $generator = $tempGenerator
  Write-Host "PRESET02_GENERATOR_SOURCE=github_main"
}

if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Staging | Out-Null
Run-Python $python @($generator, "--source", $Canonical, "--output-root", $Staging)

foreach ($mode in @("idle", "run")) {
  $src = Join-Path $Staging $mode
  $dest = Join-Path $Animations $mode
  if (-not (Test-Path $src)) { throw "PRESET02_INGRESS=BLOCKED generated_mode_missing=$mode" }
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Get-ChildItem $src -Filter "char_training_rival__${mode}__f*.png" -File | ForEach-Object {
    Move-Item $_.FullName (Join-Path $dest $_.Name) -Force
  }
}

$generatedManifest = Join-Path $Staging "manifest.json"
if (-not (Test-Path $generatedManifest)) { throw "PRESET02_INGRESS=BLOCKED p01_manifest_missing" }
Move-Item $generatedManifest (Join-Path $Lot "p01-manifest.json") -Force
Remove-Item $Staging -Recurse -Force
if ($tempGenerator -and (Test-Path $tempGenerator)) { Remove-Item $tempGenerator -Force }
Write-Host "PRESET02_P01_GENERATION=PASS"

Run-Python $python @($P01Validator)
Run-Python $python @($GlobalValidator, "--allow-incomplete")
Write-Host "PRESET02_P01_LOCAL_GATES=PASS"

git lfs install --local | Out-Null
git add -- "production/first_playable/training_rival/source/training_rival_master.png"
git add -- "production/first_playable/training_rival/first_playable_lot_01/animations/idle"
git add -- "production/first_playable/training_rival/first_playable_lot_01/animations/run"
git add -- "production/first_playable/training_rival/first_playable_lot_01/p01-manifest.json"

$staged = @(git diff --cached --name-only)
if ($staged.Count -ne 16) {
  $staged | ForEach-Object { Write-Host "PRESET02_STAGED=$_" }
  throw "PRESET02_INGRESS=BLOCKED staged_file_count=$($staged.Count) expected=16"
}
Write-Host "PRESET02_STAGED_CONTRACT=PASS files=16"

git commit -m "PRESET-02 P01: materialize exact Training Rival master and locomotion pack"
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_commit" }
$commit = (git rev-parse HEAD).Trim()

git push --set-upstream origin $Branch
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_push" }

Write-Host "PRESET02_BINARY_INGRESS=PASS"
Write-Host "PRESET02_BRANCH_PUSH=PASS branch=$Branch commit=$commit"
Write-Host "PRESET02_NEXT=OPEN_REMOTE_PR_AND_REQUIRE_SOURCE_INTAKE_PLUS_P01_PLUS_C29_PLUS_GLOBAL_PREFLIGHT"
Write-Host "PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true"
Write-Host "SIGNATURE=Tehkné Solutions"
