# QWENCP KEYWORD MAPPING
## Declared by Boss: 2026-09-17 (CORRECTED)

| Keyword | Action |
|---|---|
| **QwenCP** | Update git repo (restore point) — commit + push to remote |
| **Restore Point** | Same as above — commit + push current state to GitHub |
| **Zillion CP** | Legacy keyword (Boss uses for Zillion agent) |

## Agent Identity
- **Agent Name:** Gwen (Qwen3.8)
- **Keyword:** QwenCP (corrected from Gwen CP)
- **Repo:** https://github.com/limar01/zillion-restore
- **SD Workspace:** /storage/BDD5-1822/zillion_workspace/

## Restore Point Protocol
When Boss says "QwenCP" or "restore point":
1. Stage all changes in SD workspace
2. Commit with timestamp + summary
3. Push to remote (GitHub via SSH deploy key)
4. Report status in English

| **qwenOM** | Restore PC Omarchy (CF Tunnel Primary + MQTT Backup) |
