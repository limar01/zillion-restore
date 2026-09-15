<#
.SYNOPSIS
    Zillion Restore — Windows PowerShell Edition (zillionPS / zillionWin)
.DESCRIPTION
    Restores, bootstraps, and configures the Zillion environment on a Windows machine.
    1. Fetches the HMAC key via keyless bootstrap from the active phone gateway.
    2. Writes and protects ~/arenabridge/arenabridge.key with strict NTFS ACLs.
    3. Sets up ~/arenabridge directory structure and approval policies.
    4. Deploys the ArenaBridge Windows worker (lane: win).
    5. Verifies Python & paho-mqtt dependencies.
    6. Launches the background worker and exposes interactive helper cmdlets.
.PARAMETER Passphrase
    The bootstrap passphrase (e.g. 7YBVK-FUGXR-Q7887). Prompted if omitted.
.PARAMETER TunnelUrl
    Optional tunnel URL override. If omitted, reads local url.txt or GitHub raw.
.PARAMETER Lane
    MQTT execution lane (default: "win").
.PARAMETER Foreground
    Run the worker in the foreground window instead of background.
.PARAMETER NoWorker
    Perform setup and key delivery only, without launching the worker.
.PARAMETER CheckOnly
    Verify existing installation and connection health without re-bootstrapping.
.EXAMPLE
    .\zillionPS.ps1 -Passphrase "7YBVK-FUGXR-Q7887"
.EXAMPLE
    .\zillionPS.ps1
.EXAMPLE
    irm https://raw.githubusercontent.com/limar01/zillion-restore/main/zillionPS.ps1 | iex
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0, HelpMessage = "Zillion bootstrap passphrase")]
    [string]$Passphrase,

    [Parameter(HelpMessage = "Tunnel URL override (e.g. https://...trycloudflare.com)")]
    [string]$TunnelUrl,

    [Parameter(HelpMessage = "MQTT lane (win / pc / cp)")]
    [string]$Lane = "win",

    [Parameter(HelpMessage = "Run worker in foreground")]
    [switch]$Foreground,

    [Parameter(HelpMessage = "Do not start worker after restore")]
    [switch]$NoWorker,

    [Parameter(HelpMessage = "Verify existing installation only")]
    [switch]$CheckOnly
)

# Enforce TLS 1.2 / TLS 1.3 for modern HTTPS requests in Windows PowerShell 5.1 & 7+
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

# ----------------- UI / LOGGING HELPERS -----------------
function Write-Header {
    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Cyan
    Write-Host "  ⚡ ZILLION RESTORE — WINDOWS POWERSHELL (zillionPS / win)   " -ForegroundColor Cyan
    Write-Host "==============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([int]$Step, [int]$Total, [string]$Title)
    Write-Host "[STEP $Step/$Total] " -ForegroundColor Yellow -NoNewline
    Write-Host "$Title..." -ForegroundColor White
}

function Write-OK {
    param([string]$Message)
    Write-Host "    [OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor Gray
}

function Write-WarnMsg {
    param([string]$Message)
    Write-Host "    [WARN] " -ForegroundColor DarkYellow -NoNewline
    Write-Host $Message -ForegroundColor Yellow
}

function Write-FailMsg {
    param([string]$Message)
    Write-Host "    [FAIL] " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor Red
}

# ----------------- PATHS & CONSTANTS -----------------
$SID = "53cf4a5803c91726b892e5d0785085c6"
$ArenaHome = Join-Path $env:USERPROFILE "arenabridge"
$KeyFile = Join-Path $ArenaHome "arenabridge.key"
$ApprovalsFile = Join-Path $ArenaHome "approvals.json"
$MirrorDir = Join-Path $ArenaHome "workspace_mirror"
$WorkerFile = Join-Path $ArenaHome "worker.py"
$RawRepoUrl = "https://raw.githubusercontent.com/limar01/zillion-restore/main"

# ----------------- MAIN RESTORE FLOW -----------------
Write-Header

$TotalSteps = 6

# --- STEP 1: Verify Python Environment ---
Write-Step 1 $TotalSteps "Checking Python and dependencies"
$PythonCmd = $null
$PyCandidates = @("python", "py -3", "python3")

foreach ($cand in $PyCandidates) {
    try {
        $parts = $cand -split " "
        $bin = $parts[0]
        $args = if ($parts.Length -gt 1) { $parts[1..($parts.Length - 1)] } else { @() }
        $verOut = & $bin @args --version 2>&1
        if ($LASTEXITCODE -eq 0 -or $verOut -match "Python 3\.") {
            $PythonCmd = $cand
            Write-OK "Found Python: $verOut ($cand)"
            break
        }
    } catch { }
}

if (-not $PythonCmd) {
    Write-WarnMsg "Python 3 not found in PATH."
    Write-Host "    Please install Python 3 (e.g. 'winget install Python.Python.3.12') or add it to PATH." -ForegroundColor Yellow
} else {
    # Check paho-mqtt
    $parts = $PythonCmd -split " "
    $bin = $parts[0]
    $args = if ($parts.Length -gt 1) { $parts[1..($parts.Length - 1)] } else { @() }
    $pahoCheck = & $bin @args -c "import paho.mqtt; print('OK')" 2>&1
    if ($pahoCheck -match "OK") {
        Write-OK "Dependency 'paho-mqtt' is installed."
    } else {
        Write-Host "    [*] Installing paho-mqtt via pip..." -ForegroundColor Cyan
        & $bin @args -m pip install --quiet paho-mqtt 2>&1 | Out-Null
        $recheck = & $bin @args -c "import paho.mqtt; print('OK')" 2>&1
        if ($recheck -match "OK") {
            Write-OK "Successfully installed 'paho-mqtt'."
        } else {
            Write-WarnMsg "Could not automatically install paho-mqtt. Worker may need manual 'pip install paho-mqtt'."
        }
    }
}

# --- STEP 2: Resolve Trusted Gateway URL ---
Write-Step 2 $TotalSteps "Resolving Phone Gateway Tunnel URL"

if (-not $TunnelUrl) {
    # Try local url.txt first if executing within clone
    $LocalUrlFile = if ($PSScriptRoot) { Join-Path $PSScriptRoot "url.txt" } else { "url.txt" }
    if (Test-Path $LocalUrlFile) {
        $TunnelUrl = (Get-Content $LocalUrlFile -Raw).Trim()
        Write-OK "Loaded tunnel URL from local url.txt: $TunnelUrl"
    } else {
        # Fetch trusted URL from public GitHub repository
        try {
            Write-Host "    [*] Fetching trusted URL from GitHub raw..." -ForegroundColor Gray
            $urlReq = Invoke-WebRequest -Uri "$RawRepoUrl/url.txt" -UseBasicParsing -TimeoutSec 10
            $TunnelUrl = $urlReq.Content.Trim()
            Write-OK "Retrieved tunnel URL from GitHub: $TunnelUrl"
        } catch {
            Write-WarnMsg "Could not fetch url.txt from GitHub: $_"
        }
    }
}

if (-not $TunnelUrl) {
    $TunnelUrl = Read-Host "    [?] Enter Cloudflare or Fallback Tunnel URL"
    $TunnelUrl = $TunnelUrl.Trim().TrimEnd('/')
} else {
    $TunnelUrl = $TunnelUrl.Trim().TrimEnd('/')
}

# Test Tunnel Reachability
$TunnelReachable = $false
try {
    $pingTest = Invoke-WebRequest -Uri "$TunnelUrl/ping" -UseBasicParsing -TimeoutSec 8 -Method Get
    if ($pingTest.StatusCode -eq 200) {
        $TunnelReachable = $true
        Write-OK "Gateway /ping endpoint returned HTTP 200 (Active)."
    }
} catch {
    Write-WarnMsg "Tunnel ping check failed or timed out ($($_.Exception.Message)). Will attempt bootstrap anyway."
}

# --- STEP 3: Keyless Bootstrap & Strict Storage ---
Write-Step 3 $TotalSteps "Bootstrapping HMAC Key"

$Key = ""
if ($CheckOnly -and (Test-Path $KeyFile)) {
    $existing = (Get-Content $KeyFile -Raw).Trim()
    if ($existing.Length -eq 32) {
        $Key = $existing
        Write-OK "Existing 32-byte key found at $KeyFile."
    }
}

if (-not $Key) {
    if (-not $Passphrase) {
        $Passphrase = Read-Host "    [?] Enter Zillion restore passphrase (e.g. 7YBVK-FUGXR-Q7887)"
        $Passphrase = $Passphrase.Trim()
    }

    if (-not $Passphrase) {
        Write-FailMsg "No passphrase provided. Cannot bootstrap HMAC key."
        return
    }

    $bootstrapPayload = @{ op = "bootstrap"; pass = $Passphrase } | ConvertTo-Json -Compress
    try {
        $respRaw = Invoke-RestMethod -Uri "$TunnelUrl/" -Method Post -Body $bootstrapPayload -ContentType "application/json" -TimeoutSec 15
        if ($respRaw.PSObject.Properties['d']) {
            $inner = $respRaw.d | ConvertFrom-Json
            if ($inner.ok -and $inner.key) {
                $Key = $inner.key.Trim()
            } elseif ($inner.error) {
                Write-FailMsg "Gateway reported bootstrap error: $($inner.error)"
                return
            }
        } elseif ($respRaw.PSObject.Properties['key']) {
            $Key = $respRaw.key.Trim()
        }
    } catch {
        Write-FailMsg "HTTP request failed during bootstrap: $($_.Exception.Message)"
        return
    }

    if ($Key -and $Key.Length -eq 32) {
        Write-OK "HMAC Key successfully bootstrapped (Key length: 32 bytes; contents NOT echoed)."
    } else {
        Write-FailMsg "Received invalid key format from gateway."
        return
    }

    # Ensure target directory exists
    if (-not (Test-Path $ArenaHome)) {
        New-Item -Path $ArenaHome -ItemType Directory -Force | Out-Null
    }

    # Write key file safely
    [System.IO.File]::WriteAllText($KeyFile, "$Key`n", [System.Text.Encoding]::ASCII)

    # Restrict NTFS ACLs to current user only (equivalent to chmod 600)
    try {
        $acl = Get-Acl -Path $KeyFile
        $acl.SetAccessRuleProtection($true, $false)
        $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $currentUser,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
        $acl.ResetAccessRule($rule)
        Set-Acl -Path $KeyFile -AclObject $acl
        Write-OK "Key saved to $KeyFile with restricted user ACLs."
    } catch {
        Write-WarnMsg "Could not restrict NTFS ACL: $_"
    }
}

# --- STEP 4: Setup Directories & Approvals Policy ---
Write-Step 4 $TotalSteps "Configuring ArenaBridge Directories & Approvals"

if (-not (Test-Path $MirrorDir)) {
    New-Item -Path $MirrorDir -ItemType Directory -Force | Out-Null
    Write-OK "Created mirror directory: $MirrorDir"
}

# Approvals policy: outside_ok: true by default
$approvalsContent = @{
    outside_ok = $true
    pending = @{}
} | ConvertTo-Json -Compress

Set-Content -Path $ApprovalsFile -Value $approvalsContent -Encoding UTF8
Write-OK "Configured approvals policy: $ApprovalsFile (outside_ok: true)"

# Check D:\ drive for unrestricted subtree
if (Test-Path "D:\") {
    $DArena = "D:\arenabridge"
    if (-not (Test-Path $DArena)) {
        try {
            New-Item -Path $DArena -ItemType Directory -Force | Out-Null
            Write-OK "Initialized D:\arenabridge workspace directory."
        } catch { }
    }
}

# --- STEP 5: Deploy Worker & Runner Scripts ---
Write-Step 5 $TotalSteps "Deploying ArenaBridge Worker for Windows"

# Locate source worker.py
$SourceWorker = if ($PSScriptRoot) {
    $cand1 = Join-Path $PSScriptRoot "phone\worker.py"
    $cand2 = Join-Path $PSScriptRoot "worker.py"
    if (Test-Path $cand1) { $cand1 } elseif (Test-Path $cand2) { $cand2 } else { $null }
} else { $null }

if ($SourceWorker -and (Test-Path $SourceWorker)) {
    Copy-Item -Path $SourceWorker -Destination $WorkerFile -Force
    Write-OK "Copied worker.py from local repository: $SourceWorker -> $WorkerFile"
} else {
    Write-Host "    [*] Fetching worker.py from GitHub raw repository..." -ForegroundColor Gray
    try {
        $workerCode = (Invoke-WebRequest -Uri "$RawRepoUrl/phone/worker.py" -UseBasicParsing -TimeoutSec 15).Content
        Set-Content -Path $WorkerFile -Value $workerCode -Encoding UTF8
        Write-OK "Downloaded worker.py -> $WorkerFile"
    } catch {
        Write-WarnMsg "Could not download worker.py: $_"
    }
}

# Generate start_worker.cmd
$CmdLauncher = Join-Path $ArenaHome "start_worker.cmd"
$CmdContent = @"
@echo off
title ArenaBridge Worker (Windows Lane: $Lane)
set ZILLION_LANE=$Lane
set BRIDGE_CWD=%USERPROFILE%\arenabridge
cd /d "%USERPROFILE%\arenabridge"
echo =========================================================
echo   Starting Zillion ArenaBridge Worker (Lane: $Lane)
echo =========================================================
python worker.py
pause
"@
Set-Content -Path $CmdLauncher -Value $CmdContent -Encoding ASCII
Write-OK "Created launcher script: $CmdLauncher"

# Generate start_worker.ps1
$PsLauncher = Join-Path $ArenaHome "start_worker.ps1"
$PsContent = @"
`$env:ZILLION_LANE = "$Lane"
`$env:BRIDGE_CWD = "$ArenaHome"
Set-Location "$ArenaHome"
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "  Starting Zillion ArenaBridge Worker (Lane: $Lane)" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
python worker.py
"@
Set-Content -Path $PsLauncher -Value $PsContent -Encoding UTF8
Write-OK "Created PowerShell launcher: $PsLauncher"

# Generate stop_worker.ps1
$StopScript = Join-Path $ArenaHome "stop_worker.ps1"
$StopContent = @"
Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object {
    try {
        `$cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = `$(`$_.Id)").CommandLine
        `$cmd -like "*worker.py*"
    } catch { `$false }
} | Stop-Process -Force
Write-Host "[OK] Stopped Zillion worker process(es)." -ForegroundColor Green
"@
Set-Content -Path $StopScript -Value $StopContent -Encoding UTF8
Write-OK "Created stop script: $StopScript"

# --- STEP 6: Worker Launch & Status ---
Write-Step 6 $TotalSteps "Worker Status & Background Startup"

if ($NoWorker) {
    Write-OK "Worker launch skipped (-NoWorker flag)."
} elseif (-not $PythonCmd) {
    Write-WarnMsg "Cannot launch worker because Python was not detected."
} else {
    if ($Foreground) {
        Write-Host "`n[*] Starting ArenaBridge worker in foreground (Ctrl+C to stop)...`n" -ForegroundColor Green
        $env:ZILLION_LANE = $Lane
        $env:BRIDGE_CWD = $ArenaHome
        Set-Location $ArenaHome
        $parts = $PythonCmd -split " "
        $bin = $parts[0]
        $args = if ($parts.Length -gt 1) { $parts[1..($parts.Length - 1)] } else { @() }
        & $bin @args worker.py
    } else {
        # Check if already running
        $alreadyRunning = $false
        Get-Process python, pythonw -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
                if ($cmd -like "*worker.py*") { $alreadyRunning = $true }
            } catch { }
        }

        if ($alreadyRunning) {
            Write-OK "Worker is already running in background."
        } else {
            Write-Host "    [*] Starting worker in background..." -ForegroundColor Cyan
            $parts = $PythonCmd -split " "
            $bin = $parts[0]

            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = $bin
            $psi.Arguments = "worker.py"
            $psi.WorkingDirectory = $ArenaHome
            $psi.EnvironmentVariables["ZILLION_LANE"] = $Lane
            $psi.EnvironmentVariables["BRIDGE_CWD"] = $ArenaHome
            $psi.UseShellExecute = $false
            $psi.CreateNoWindow = $true

            [System.Diagnostics.Process]::Start($psi) | Out-Null
            Start-Sleep -Seconds 2
            Write-OK "ArenaBridge worker started in background (Lane: $Lane)."
        }
    }
}

# ----------------- SUMMARY & CMDLETS -----------------
Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  ✅ ZILLION WINDOWS RESTORE COMPLETE                        " -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "  Home Dir  : $ArenaHome" -ForegroundColor Gray
Write-Host "  Key File  : $KeyFile (Protected)" -ForegroundColor Gray
Write-Host "  MQTT Lane : $Lane (Topic: arenabridge/$SID/$Lane/cmd)" -ForegroundColor Gray
Write-Host "  Gateway   : $TunnelUrl" -ForegroundColor Gray
Write-Host "==============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Helper cmdlets available in this PowerShell session:" -ForegroundColor Cyan
Write-Host "  - Invoke-ZillionExec -Command 'dir' [-Target win|phone]" -ForegroundColor White
Write-Host "  - Get-ZillionStatus" -ForegroundColor White
Write-Host "  - Start-ZillionWorker" -ForegroundColor White
Write-Host "  - Stop-ZillionWorker" -ForegroundColor White
Write-Host ""

# ----------------- SESSION HELPER FUNCTIONS -----------------
function global:Get-ZillionHmac {
    param([string]$Key, [string]$Message)
    $hmac = New-Object System.Security.Cryptography.HMACSHA256
    $hmac.Key = [System.Text.Encoding]::UTF8.GetBytes($Key)
    $hash = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Message))
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function global:Invoke-ZillionExec {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Command,
        [ValidateSet("phone", "win")]
        [string]$Target = "phone",
        [int]$TimeoutSec = 30
    )

    $kFile = Join-Path $env:USERPROFILE "arenabridge\arenabridge.key"
    if (-not (Test-Path $kFile)) {
        Write-Error "Key file not found at $kFile."
        return
    }
    $k = (Get-Content $kFile -Raw).Trim()

    if ($Target -eq "phone") {
        $uFile = Join-Path $env:USERPROFILE "arenabridge\tunnel_url.txt"
        $tu = if (Test-Path $uFile) { (Get-Content $uFile -Raw).Trim() } else { $script:TunnelUrl }
        if (-not $tu) {
            Write-Error "No phone tunnel URL configured."
            return
        }

        $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $rid = "ps_" + [Guid]::NewGuid().ToString("N").Substring(0, 6)
        $payloadObj = @{
            op = "exec"
            id = $rid
            cmd = $Command
            timeout = $TimeoutSec
            ts = $now
        }
        $d = $payloadObj | ConvertTo-Json -Compress
        $h = Get-ZillionHmac -Key $k -Message $d
        $envelope = @{ d = $d; h = $h } | ConvertTo-Json -Compress

        try {
            $resp = Invoke-RestMethod -Uri "$tu/" -Method Post -Body $envelope -ContentType "application/json" -TimeoutSec ($TimeoutSec + 10)
            if ($resp.PSObject.Properties['d']) {
                $out = $resp.d | ConvertFrom-Json
                if ($out.output) { Write-Host $out.output }
                if ($out.stderr) { Write-Host $out.stderr -ForegroundColor DarkYellow }
                return $out
            } else {
                return $resp
            }
        } catch {
            Write-Error "Exec failed: $($_.Exception.Message)"
        }
    } else {
        Write-Host "[*] Executing locally via worker environment..." -ForegroundColor Gray
        Invoke-Expression $Command
    }
}

function global:Get-ZillionStatus {
    Write-Host "`n--- Zillion Windows Node Status ---" -ForegroundColor Cyan
    $kFile = Join-Path $env:USERPROFILE "arenabridge\arenabridge.key"
    Write-Host "Key file exists : $(Test-Path $kFile)"
    
    $workerRunning = $false
    Get-Process python, pythonw -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            if ($cmd -like "*worker.py*") { $workerRunning = $true }
        } catch { }
    }
    Write-Host "Worker active   : $workerRunning"
    
    if ($script:TunnelUrl) {
        try {
            $p = Invoke-WebRequest -Uri "$($script:TunnelUrl)/ping" -UseBasicParsing -TimeoutSec 5
            Write-Host "Phone Gateway   : $($script:TunnelUrl) (HTTP $($p.StatusCode))"
        } catch {
            Write-Host "Phone Gateway   : $($script:TunnelUrl) (Unreachable: $($_.Exception.Message))" -ForegroundColor Yellow
        }
    }
    Write-Host ""
}

function global:Start-ZillionWorker {
    $aHome = Join-Path $env:USERPROFILE "arenabridge"
    $wFile = Join-Path $aHome "worker.py"
    if (-not (Test-Path $wFile)) {
        Write-Error "worker.py not found in $aHome"
        return
    }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = "worker.py"
    $psi.WorkingDirectory = $aHome
    $psi.EnvironmentVariables["ZILLION_LANE"] = "win"
    $psi.EnvironmentVariables["BRIDGE_CWD"] = $aHome
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Write-Host "[OK] Started ArenaBridge worker in background." -ForegroundColor Green
}

function global:Stop-ZillionWorker {
    $sScript = Join-Path $env:USERPROFILE "arenabridge\stop_worker.ps1"
    if (Test-Path $sScript) {
        & $sScript
    } else {
        Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
                $cmd -like "*worker.py*"
            } catch { $false }
        } | Stop-Process -Force
        Write-Host "[OK] Stopped worker process(es)." -ForegroundColor Green
    }
}
