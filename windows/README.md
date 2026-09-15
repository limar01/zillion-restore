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
