# 💻 Zillion Windows Node (`zillionWin` / `zillionPS`)

This folder contains the Windows restoration and runtime files for ArenaBridge.

## Quick Start
In PowerShell (as Administrator or regular user):
```powershell
.\zillionPS.ps1 <PASSPHRASE>
```
Or double-click / run:
```cmd
zillionPS.cmd <PASSPHRASE>
```

## Features
- **Keyless Bootstrap**: Retrieves the HMAC signing key automatically from the active phone gateway.
- **Security**: Protects `arenabridge.key` using strict NTFS user ACLs.
- **Worker**: Runs `worker.py` on lane `win` (`arenabridge/<SID>/win/{cmd,res,pres}`).
- **Interactive Tools**: Built-in helper cmdlets (`Invoke-ZillionExec`, `Get-ZillionStatus`, `Start-ZillionWorker`, `Stop-ZillionWorker`).

## Repair (flapping/dead lane)
If the lane flaps or dies (usual cause: duplicate `worker.py` instances fighting over one MQTT client ID), run the repair script — it stops all workers, downloads the latest `worker.py` (v4.5.2+: single-instance lock + unique client IDs + reconnect backoff), and starts exactly one:
```powershell
Invoke-WebRequest https://raw.githubusercontent.com/limar01/zillion-restore/main/windows/REPAIR.cmd -OutFile $env:USERPROFILE\arenabridge\REPAIR.cmd -UseBasicParsing
& $env:USERPROFILE\arenabridge\REPAIR.cmd
```
Keep the laptop awake while working (sleep drops the MQTT link).
