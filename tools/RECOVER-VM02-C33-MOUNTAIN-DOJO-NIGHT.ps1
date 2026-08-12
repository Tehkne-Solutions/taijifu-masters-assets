param(
    [string]$Workspace = "W:\TEHKNE-SOLUTIONS\PROJETOS\JOGO-TAIJIFU-MASTERS",
    [string]$TargetBranch = "agent/vfx02-arena-source-recovery"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$AssetsRepo = Join-Path $Workspace "taijifu-masters-assets"
$GameRepo = Join-Path $Workspace "taijifu-masters"
$OriginalZip = Join-Path $Workspace "TAIJIFU_VM02_C33_MOUNTAIN_DOJO_NIGHT_ART.zip"
$CanonicalDir = Join-Path $AssetsRepo "packs\stages\mountain_dojo_night\v1"
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("taijifu-c33-recovery-" + [Guid]::NewGuid().ToString("N"))

$Expected = [ordered]@{
    "background.png" = 11053
    "midground.png"  = 9978
    "foreground.png" = 6715
}

$CanonicalGitPaths = @(
    "packs/stages/mountain_dojo_night/v1/background.png",
    "packs/stages/mountain_dojo_night/v1/midground.png",
    "packs/stages/mountain_dojo_night/v1/foreground.png"
)
$EvidenceGitPath = "packs/stages/mountain_dojo_night/v1/C33_RECOVERY_EVIDENCE.json"
$AllRecoveryGitPaths = @($CanonicalGitPaths + @($EvidenceGitPath))

function Invoke-GitChecked {
    param(
        [Parameter(Mandatory=$true)][string[]]$Args,
        [Parameter(Mandatory=$true)][string]$Failure
    )

    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & git -C $AssetsRepo @Args 2>&1
        $exit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }

    if ($output) {
        $output | ForEach-Object { Write-Host $_ }
    }
    if ($exit -ne 0) {
        throw "$Failure exit=$exit"
    }
}

function Invoke-GitCapture {
    param(
        [Parameter(Mandatory=$true)][string[]]$Args,
        [Parameter(Mandatory=$true)][string]$Failure
    )

    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = (& git -C $AssetsRepo @Args 2>&1) -join "`n"
        $exit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }

    if ($exit -ne 0) {
        throw "$Failure exit=$exit output=$output"
    }
    return $output
}

function Get-PngInfo {
    param([Parameter(Mandatory=$true)][string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 24) {
        throw "C33_RECOVERY_PNG=BLOCKED file=$Path reason=too_small"
    }

    $signature = @(137,80,78,71,13,10,26,10)
    for ($i = 0; $i -lt 8; $i++) {
        if ([int]$bytes[$i] -ne $signature[$i]) {
            throw "C33_RECOVERY_PNG=BLOCKED file=$Path reason=invalid_signature"
        }
    }

    $width = ([int]$bytes[16] -shl 24) -bor ([int]$bytes[17] -shl 16) -bor ([int]$bytes[18] -shl 8) -bor [int]$bytes[19]
    $height = ([int]$bytes[20] -shl 24) -bor ([int]$bytes[21] -shl 16) -bor ([int]$bytes[22] -shl 8) -bor [int]$bytes[23]

    [pscustomobject]@{
        Width = $width
        Height = $height
        Size = $bytes.Length
        Sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

function Test-CandidateSet {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$SourceLabel
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return $null
    }

    $records = @()
    foreach ($name in $Expected.Keys) {
        $path = Join-Path $Root $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            return $null
        }

        $info = Get-PngInfo -Path $path
        if ($info.Size -ne $Expected[$name]) {
            throw "C33_RECOVERY_SOURCE=BLOCKED source=$SourceLabel file=$name expected_bytes=$($Expected[$name]) actual_bytes=$($info.Size)"
        }
        if ($info.Width -ne 1920 -or $info.Height -ne 1080) {
            throw "C33_RECOVERY_SOURCE=BLOCKED source=$SourceLabel file=$name expected=1920x1080 actual=$($info.Width)x$($info.Height)"
        }

        $records += [pscustomobject]@{
            file = $name
            path = $path
            bytes = $info.Size
            width = $info.Width
            height = $info.Height
            sha256 = $info.Sha256
        }
    }

    [pscustomobject]@{
        label = $SourceLabel
        root = $Root
        records = $records
    }
}

function Get-ExistingRecoveryTimestamp {
    param(
        [Parameter(Mandatory=$true)][string]$EvidencePath,
        [Parameter(Mandatory=$true)]$Source
    )

    if (-not (Test-Path -LiteralPath $EvidencePath -PathType Leaf)) {
        return $null
    }

    try {
        $existing = Get-Content -LiteralPath $EvidencePath -Raw | ConvertFrom-Json
        if ($existing.schema -ne "tehkne/taijifu-c33-source-recovery/v1") { return $null }
        if ($existing.signature -ne "Tehkné Solutions") { return $null }
        if ($existing.arena_id -ne "mountain_dojo_night") { return $null }
        if ($existing.recovery_policy -ne "original_candidate_only_no_regeneration") { return $null }
        if ($existing.source -ne $Source.label) { return $null }

        foreach ($record in $Source.records) {
            $existingRecord = @($existing.files | Where-Object { $_.file -eq $record.file }) | Select-Object -First 1
            if ($null -eq $existingRecord) { return $null }
            if ([string]$existingRecord.sha256 -ne [string]$record.sha256) { return $null }
            if ([int]$existingRecord.bytes -ne [int]$record.bytes) { return $null }
            if ([string]$existingRecord.dimensions -ne "$($record.width)x$($record.height)") { return $null }
        }

        if ([string]::IsNullOrWhiteSpace([string]$existing.recovered_at_utc)) { return $null }
        return [string]$existing.recovered_at_utc
    }
    catch {
        return $null
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $AssetsRepo ".git"))) {
    throw "C33_RECOVERY_ASSETS_REPO=BLOCKED path=$AssetsRepo"
}

New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
try {
    $source = $null

    if (Test-Path -LiteralPath $OriginalZip -PathType Leaf) {
        $zipExtract = Join-Path $TempRoot "zip"
        New-Item -ItemType Directory -Force -Path $zipExtract | Out-Null
        Expand-Archive -LiteralPath $OriginalZip -DestinationPath $zipExtract -Force
        $source = Test-CandidateSet -Root $zipExtract -SourceLabel "original_c33_zip"
        if ($null -eq $source) {
            throw "C33_RECOVERY_SOURCE=BLOCKED source=original_c33_zip reason=incomplete_three_png_set"
        }
        Write-Host "C33_RECOVERY_SOURCE=PASS source=original_c33_zip path=$OriginalZip"
    }

    if ($null -eq $source) {
        $gameCopy = Join-Path $GameRepo "assets\pack_03_stages\mountain_dojo_night"
        $source = Test-CandidateSet -Root $gameCopy -SourceLabel "local_game_repo_copy"
        if ($null -ne $source) {
            Write-Host "C33_RECOVERY_SOURCE=PASS source=local_game_repo_copy path=$gameCopy"
        }
    }

    if ($null -eq $source) {
        $c33Copy = Join-Path $Workspace "C33"
        $source = Test-CandidateSet -Root $c33Copy -SourceLabel "local_c33_extract"
        if ($null -ne $source) {
            Write-Host "C33_RECOVERY_SOURCE=PASS source=local_c33_extract path=$c33Copy"
        }
    }

    if ($null -eq $source) {
        throw "C33_RECOVERY=BLOCKED reason=original_candidate_not_found checked=zip,game_repo,C33_extract"
    }

    foreach ($record in $source.records) {
        Write-Host "C33_RECOVERY_FILE=PASS file=$($record.file) bytes=$($record.bytes) dimensions=$($record.width)x$($record.height) sha256=$($record.sha256)"
    }

    Invoke-GitChecked -Args @("fetch", "origin") -Failure "C33_RECOVERY_GIT_FETCH=BLOCKED"
    Invoke-GitChecked -Args @("switch", $TargetBranch) -Failure "C33_RECOVERY_GIT_SWITCH=BLOCKED branch=$TargetBranch"
    Invoke-GitChecked -Args @("pull", "--ff-only", "origin", $TargetBranch) -Failure "C33_RECOVERY_GIT_PULL=BLOCKED branch=$TargetBranch"

    New-Item -ItemType Directory -Force -Path $CanonicalDir | Out-Null
    foreach ($record in $source.records) {
        Copy-Item -LiteralPath $record.path -Destination (Join-Path $CanonicalDir $record.file) -Force
    }

    foreach ($name in $Expected.Keys) {
        $dest = Join-Path $CanonicalDir $name
        $destInfo = Get-PngInfo -Path $dest
        $sourceRecord = $source.records | Where-Object { $_.file -eq $name } | Select-Object -First 1
        if ($destInfo.Sha256 -ne $sourceRecord.sha256) {
            throw "C33_RECOVERY_COPY=BLOCKED file=$name reason=sha256_mismatch"
        }
        Write-Host "C33_RECOVERY_COPY=PASS file=$name sha256=$($destInfo.Sha256)"
    }

    $evidencePath = Join-Path $CanonicalDir "C33_RECOVERY_EVIDENCE.json"
    $existingRecoveredAt = Get-ExistingRecoveryTimestamp -EvidencePath $evidencePath -Source $source
    $recoveredAt = if ($existingRecoveredAt) { $existingRecoveredAt } else { [DateTime]::UtcNow.ToString("o") }

    $evidence = [ordered]@{
        schema = "tehkne/taijifu-c33-source-recovery/v1"
        signature = "Tehkné Solutions"
        arena_id = "mountain_dojo_night"
        recovery_policy = "original_candidate_only_no_regeneration"
        source = $source.label
        recovered_at_utc = $recoveredAt
        visual_promotion = "pending_runtime_and_manual_review"
        files = @($source.records | ForEach-Object {
            [ordered]@{
                file = $_.file
                bytes = $_.bytes
                dimensions = "$($_.width)x$($_.height)"
                sha256 = $_.sha256
            }
        })
    }
    $evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $evidencePath -Encoding UTF8

    # Repository policy: canonical binary art is versioned through Git LFS.
    Invoke-GitChecked -Args @("lfs", "version") -Failure "C33_RECOVERY_GIT_LFS=BLOCKED"
    foreach ($gitPath in $CanonicalGitPaths) {
        $attrOutput = Invoke-GitCapture -Args @("check-attr", "filter", "--", $gitPath) -Failure "C33_RECOVERY_LFS_POLICY=BLOCKED file=$gitPath"
        if ($attrOutput -notmatch 'filter:\s+lfs') {
            throw "C33_RECOVERY_LFS_POLICY=BLOCKED file=$gitPath attr=$attrOutput"
        }
        Write-Host "C33_RECOVERY_LFS_FILE=PASS file=$gitPath"
    }
    Write-Host "C33_RECOVERY_LFS_POLICY=PASS files=3/3"

    Invoke-GitChecked -Args @("add", "--",
        $CanonicalGitPaths[0],
        $CanonicalGitPaths[1],
        $CanonicalGitPaths[2],
        $EvidenceGitPath) -Failure "C33_RECOVERY_GIT_ADD=BLOCKED"

    # Verify the Git index directly. `git diff --cached --name-only` is not a
    # reliable presence test for this recovery because clean/smudge filters can
    # make the worktree/index presentation differ. The index entry is canonical.
    foreach ($required in $AllRecoveryGitPaths) {
        $indexEntry = Invoke-GitCapture -Args @("ls-files", "--stage", "--", $required) -Failure "C33_RECOVERY_INDEX=BLOCKED file=$required"
        if ([string]::IsNullOrWhiteSpace($indexEntry)) {
            throw "C33_RECOVERY_INDEX=BLOCKED file=$required reason=missing_index_entry"
        }
        Write-Host "C33_RECOVERY_INDEX=PASS file=$required"
    }

    # The staged representation of every PNG must be a Git LFS pointer whose
    # oid is exactly the SHA-256 of the original recovered binary.
    foreach ($gitPath in $CanonicalGitPaths) {
        $fileName = [System.IO.Path]::GetFileName($gitPath)
        $sourceRecord = $source.records | Where-Object { $_.file -eq $fileName } | Select-Object -First 1
        if ($null -eq $sourceRecord) {
            throw "C33_RECOVERY_LFS_INDEX=BLOCKED file=$gitPath reason=missing_source_record"
        }

        $pointer = Invoke-GitCapture -Args @("show", ":$gitPath") -Failure "C33_RECOVERY_LFS_INDEX=BLOCKED file=$gitPath"
        $expectedOid = "oid sha256:$($sourceRecord.sha256)"
        $expectedSize = "size $($sourceRecord.bytes)"
        if ($pointer -notmatch '(?m)^version https://git-lfs\.github\.com/spec/v1$') {
            throw "C33_RECOVERY_LFS_INDEX=BLOCKED file=$gitPath reason=not_lfs_pointer"
        }
        if ($pointer -notmatch "(?m)^$([regex]::Escape($expectedOid))$") {
            throw "C33_RECOVERY_LFS_INDEX=BLOCKED file=$gitPath reason=oid_mismatch expected=$expectedOid"
        }
        if ($pointer -notmatch "(?m)^$([regex]::Escape($expectedSize))$") {
            throw "C33_RECOVERY_LFS_INDEX=BLOCKED file=$gitPath reason=size_mismatch expected=$expectedSize"
        }
        Write-Host "C33_RECOVERY_LFS_INDEX=PASS file=$gitPath oid=sha256:$($sourceRecord.sha256)"
    }

    Write-Host "C33_RECOVERY_STAGE=PASS files=3/3 evidence=1/1"

    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & git -C $AssetsRepo diff --cached --quiet --exit-code
        $diffExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }

    if ($diffExit -eq 1) {
        Invoke-GitChecked -Args @("commit", "-m", "C33 recover original Mountain Dojo Night art`n`nTehkné Solutions") -Failure "C33_RECOVERY_COMMIT=BLOCKED"
        Write-Host "C33_RECOVERY_COMMIT=PASS state=new_commit"
    }
    elseif ($diffExit -eq 0) {
        Write-Host "C33_RECOVERY_COMMIT=PASS state=already_committed"
    }
    else {
        throw "C33_RECOVERY_COMMIT=BLOCKED reason=staged_diff_check exit=$diffExit"
    }

    Invoke-GitChecked -Args @("push", "origin", $TargetBranch) -Failure "C33_RECOVERY_PUSH=BLOCKED branch=$TargetBranch"

    $head = (& git -C $AssetsRepo rev-parse HEAD).Trim()
    Write-Host "C33_RECOVERY=PASS"
    Write-Host "C33_RECOVERY_BRANCH=$TargetBranch"
    Write-Host "C33_RECOVERY_COMMIT=$head"
    Write-Host "C33_RECOVERY_NEXT=remote_ci_then_game_intake_then_vfx02_canonical_capture"
    Write-Host "SIGNATURE=Tehkné Solutions"
}
finally {
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
