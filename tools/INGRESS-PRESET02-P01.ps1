param(
  [Parameter(Mandatory=$true)][string]$MasterPath,
  [string]$Branch = "agent/preset02-p01-binary-ingress",
  [string]$RepoRoot = "",
  [switch]$ProbePythonInvocation
)

$ErrorActionPreference = "Stop"

$ScriptPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
  throw "PRESET02_INGRESS=BLOCKED script_path_unavailable"
}
$ScriptRoot = Split-Path -Parent $ScriptPath
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = (Resolve-Path (Join-Path $ScriptRoot "..")).Path
} else {
  $RepoRoot = (Resolve-Path $RepoRoot).Path
}
if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
  throw "PRESET02_INGRESS=BLOCKED repo_root_invalid=$RepoRoot"
}
Set-Location $RepoRoot
Write-Host "PRESET02_REPO_ROOT=$RepoRoot"

$ApprovedRawSha = "de532ea47c0b16921bfb84d3826fe1a2a51cf9f10aa8f6d8b98a90d9a457be6d"
$ApprovedRawBytes = 1273838
$ReferenceCanonicalSha = "ce76243a4b89147a4900e823041b5392e2b19b13549aaa9fcd95cbf3e34d3fe3"
$ReferenceCanonicalBytes = 747624
$Canonical = Join-Path $RepoRoot "production\first_playable\training_rival\source\training_rival_master.png"
$Lot = Join-Path $RepoRoot "production\first_playable\training_rival\first_playable_lot_01"
$Animations = Join-Path $Lot "animations"
$Staging = Join-Path $Lot "__p01_ingress_staging"
$Canonicalizer = Join-Path $RepoRoot "tools\canonicalize_training_rival_master.py"
$Generator = Join-Path $RepoRoot "tools\materialize_training_rival_p01_weapon_safe.py"
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

function Run-Python {
  param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string[]]$PythonArgs
  )
  Write-Host "PRESET02_PYTHON_EXEC=$Python args=$($PythonArgs -join ' ')"
  if ($Python -eq "py") { & py -3 @PythonArgs }
  else { & $Python @PythonArgs }
  if ($LASTEXITCODE -ne 0) {
    throw "PRESET02_INGRESS=BLOCKED python_exit=$LASTEXITCODE args=$($PythonArgs -join ' ')"
  }
}

function Require-Pillow([string]$Python) {
  if ($Python -eq "py") { & py -3 -c "import PIL; print('PRESET02_PILLOW_VERSION=' + PIL.__version__)" }
  else { & $Python -c "import PIL; print('PRESET02_PILLOW_VERSION=' + PIL.__version__)" }
  if ($LASTEXITCODE -ne 0) {
    throw "PRESET02_INGRESS=BLOCKED Pillow_missing install_with='py -3 -m pip install Pillow'"
  }
}

if ($ProbePythonInvocation) {
  $probePython = Resolve-Python
  $probeCode = 'import sys; assert sys.argv[1:] == ["probe-a", "probe-b"]; print("PRESET02_PYTHON_ARGV=PASS")'
  Run-Python -Python $probePython -PythonArgs @("-c", $probeCode, "probe-a", "probe-b")
  Write-Host "PRESET02_PYTHON_INVOCATION_PROBE=PASS"
  Write-Host "SIGNATURE=Tehkné Solutions"
  exit 0
}

if (-not (Test-Path $MasterPath -PathType Leaf)) { throw "PRESET02_INGRESS=BLOCKED master_missing=$MasterPath" }
$MasterPath = (Resolve-Path $MasterPath).Path
$actualBytes = (Get-Item $MasterPath).Length
$actualSha = (Get-FileHash $MasterPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "PRESET02_MASTER_BYTES=$actualBytes"
Write-Host "PRESET02_MASTER_SHA256=$actualSha"

$inputKind = ""
if ($actualBytes -eq $ApprovedRawBytes -and $actualSha -eq $ApprovedRawSha) {
  $inputKind = "approved_original_raw"
} elseif ($actualBytes -eq $ReferenceCanonicalBytes -and $actualSha -eq $ReferenceCanonicalSha) {
  $inputKind = "reference_canonical_exact"
} else {
  throw "PRESET02_INGRESS=BLOCKED input_not_approved raw_expected=$ApprovedRawSha/$ApprovedRawBytes canonical_expected=$ReferenceCanonicalSha/$ReferenceCanonicalBytes"
}
Write-Host "PRESET02_APPROVED_INPUT=PASS kind=$inputKind"

foreach ($required in @($Canonicalizer, $Generator, $SourceValidator, $P01Validator, $GlobalValidator)) {
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

# A failed prior ingress may have created the local target branch before any commit.
# Reuse it only when it has no commits not already contained in origin/main and no remote branch exists.
git ls-remote --exit-code --heads origin "refs/heads/$Branch" | Out-Null
$remoteBranchExists = ($LASTEXITCODE -eq 0)
git show-ref --verify --quiet "refs/heads/$Branch"
$localBranchExists = ($LASTEXITCODE -eq 0)

if ($remoteBranchExists) {
  throw "PRESET02_INGRESS=BLOCKED remote_branch_exists=$Branch"
}

if ($localBranchExists) {
  $uniqueCommitsText = (git rev-list --count "origin/main..$Branch").Trim()
  if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED local_branch_inspection_failed=$Branch" }
  $uniqueCommits = [int]$uniqueCommitsText
  if ($uniqueCommits -ne 0) {
    throw "PRESET02_INGRESS=BLOCKED local_branch_has_unique_commits=$Branch count=$uniqueCommits"
  }
  git branch -f $Branch origin/main
  if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED local_branch_reset_failed=$Branch" }
  git switch $Branch
  if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED local_branch_switch_failed=$Branch" }
  Write-Host "PRESET02_BRANCH=PASS name=$Branch resumed_clean_local=true"
} else {
  git switch -c $Branch origin/main
  if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED branch_create" }
  Write-Host "PRESET02_BRANCH=PASS name=$Branch resumed_clean_local=false"
}

$python = Resolve-Python
Require-Pillow $python

New-Item -ItemType Directory -Force -Path (Split-Path $Canonical -Parent) | Out-Null
Run-Python -Python $python -PythonArgs @($Canonicalizer, "--source", $MasterPath, "--output", $Canonical)
Write-Host "PRESET02_CANONICAL_MASTER_COPY=PASS source_kind=$inputKind"

Run-Python -Python $python -PythonArgs @($SourceValidator)
Write-Host "PRESET02_SOURCE_INTAKE_LOCAL=PASS"

if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Staging | Out-Null
Run-Python -Python $python -PythonArgs @($Generator, "--source", $Canonical, "--output-root", $Staging)

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
Write-Host "PRESET02_P01_GENERATION=PASS method=weapon_safe_v3"

Run-Python -Python $python -PythonArgs @($P01Validator)
Run-Python -Python $python -PythonArgs @($GlobalValidator, "--allow-incomplete")
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

git commit -m "PRESET-02 P01: materialize approved Training Rival master and weapon-safe locomotion"
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_commit" }
$commit = (git rev-parse HEAD).Trim()

git push --set-upstream origin $Branch
if ($LASTEXITCODE -ne 0) { throw "PRESET02_INGRESS=BLOCKED git_push" }

Write-Host "PRESET02_BINARY_INGRESS=PASS"
Write-Host "PRESET02_BRANCH_PUSH=PASS branch=$Branch commit=$commit"
Write-Host "PRESET02_NEXT=OPEN_REMOTE_PR_AND_REQUIRE_SOURCE_INTAKE_PLUS_P01_PLUS_C29_PLUS_GLOBAL_PREFLIGHT"
Write-Host "PRESET02_RUNTIME_PROMOTION=BLOCKED requires_44_of_44=true"
Write-Host "SIGNATURE=Tehkné Solutions"
