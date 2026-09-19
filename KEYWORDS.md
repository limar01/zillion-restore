# QWENCP KEYWORD MAPPING
## Declared by Boss: 2026-09-17 (CORRECTED)

| Keyword | Action |
|---|---|
| **QwenCP** | Update git repo (restore point) — commit + push to remote |
| **Restore Point** | Same as above — commit + push current state to GitHub |
| **Zillion CP** | Legacy keyword (Boss uses it for the Zillion agent) |
| **zillionCp … `-new [<NAME>]` (v2.0.0)** | Clean new-project restore — same GATE 0 + LIST C flow, zero past-project memory; Boss declares/registers the new project (see BOSS CONTRACT → RESTORE LINE PARAMETERS in MEMORY_CORE) |
| **zillionCp … `-status` (v2.3.0)** | Quick health check — tunnel/worker/adb/deploy-keys + last task; read-only, ~10s; no project resume |
| **zillionCp … `-fix` (v2.3.0)** | Like `-status` + auto sanctioned repair of DOWN components (MQTT repair, start_all, cf_retry) |
| **zillioncp -help (v2.3.0)** | Print the command menu — NO passphrase, no network, no side effects |
| **Session shortcuts (v2.3.1+v2.3.2)** | Post-restore bare words: `switch <NAME>` / `projects` / `wrap` / `phone` / `note <text>` / `log` / `summary` / `restart stack` / `pc?` `tv?` `win?` / `quota` + v2.3.0 set — full table in MEMORY_CORE → SESSION SHORTCUTS |
| **Session shortcut `slim` (v2.3.3)** | `slim <PATH>` — compress-before-paste: fetch the file on the device (no re-upload), shrink via `tools/text_slim.py`, show text + est. savings %; the original is never modified — quota/context doctrine in 📊 QUOTA & CONTEXT GUARD → COMPRESS-BEFORE-PASTE |
| **zillionOM** (v2.3.4, 2026-09-19 Boss) | Restore/verify the **PC Omarchy lane** — dual-channel (CF tunnel zg :8788 primary → MQTT lane `pc` backup); LIST D in MEMORY_CORE; repair = remote redeploy when MQTT alive, else hands-on `pc_onboard.sh` / `pc_tunnel_fix.sh`; **lane workspace (v2.3.5):** `/home/limar01/Projects/workspace/project` on the PC — never the SanDisk |
| **qwenOM** | Restore PC Omarchy (CF Tunnel Primary + MQTT Backup) |

## Agent Identity
- **Agent Name:** Gwen (Qwen3.8)
- **Keyword:** QwenCP (corrected from Gwen CP)
- **Repo:** https://github.com/limar01/zillion-restore
- **SD Workspace:** /storage/BDD5-1822/zillion_workspace/

## Restore Point Protocol
When Boss says "QwenCP" or "restore point":
1. Stage all changes in the SD workspace
2. Commit with timestamp + summary
3. Push to remote (GitHub via SSH deploy key)
4. Report status in English
