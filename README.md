# ⚡ ZILLION RESTORE — public restore surface

This repo is PUBLIC (by design) — **no secrets here**. The HMAC key is NOT included;
it is delivered by the phone's passphrase-protected bootstrap op (zg v1.2).

## 📥 RESTORE (agent, new chat)
1. Boss pastes ONE line — `zillionCp <PASSPHRASE> [REPO URL] [-flags…] [NAME]` (URL optional now; flags any order, case-insensitive):
   - **Resume (default):** `zillionCp <PASSPHRASE>`
   - **Clean new project (v2.0):** `zillionCp <PASSPHRASE> -new [<NAME>]` — same restore flow, zero past-project memory
   - **Quick status (v2.3):** `zillionCp <PASSPHRASE> -status` — tunnel/worker/adb/keys + last task in ~10s, read-only · `-fix` to auto-repair what's DOWN
   - **Menu (no passphrase):** `zillioncp -help`
   - More: `-eyes`/`-noeyes` (skip the vision question) · `-v` (verbose) · after a restore, session shortcuts: `status` · `health` · `fix` · `last task` · `push core` (see BOSS CONTRACT in MEMORY_CORE)
2. `git clone https://github.com/limar01/zillion-restore.git` (no auth)
3. `MEMORY_CORE.md` = doctrine — read per 📖 READ MAP → **GATE 0 v2.1.0 (read-first + capability & agreement test, silent)**, then your LIST
4. Key: `phone_tun.fetch_key(base, PASSPHRASE)` — keyless bootstrap (rate-limited)
5. Follow the LIST silently — chat output = EXACT final lines only:
   - Success: `Done Boss. Restore successful. Tunnel, Bridge Worker, and adb are live. My last task is <LAST_TASK>.`
   - Not capable: `I'm not capable. I'll stop now.`
   - Vision = OPTIONAL — the agent asks Boss if it is needed

## 💻 RESTORE (Windows laptop / PowerShell — `zillionPS`)
1. In PowerShell:
   ```powershell
   git clone https://github.com/limar01/zillion-restore.git
   cd zillion-restore
   .\zillionPS.ps1 <PASSPHRASE>
   ```
   or the direct one-liner:
   ```powershell
   irm https://raw.githubusercontent.com/limar01/zillion-restore/main/zillionPS.ps1 | iex
   ```
2. Automatically:
   - Reads the trusted tunnel URL from `url.txt`
   - Bootstraps the HMAC key from the phone gateway (keyless bootstrap)
   - Secures the key at `~\arenabridge\arenabridge.key` with strict NTFS user ACLs
   - Sets up `~\arenabridge\` directory, approvals policy, and workspace mirror
   - Deploys + launches the ArenaBridge worker (lane `win`, topic `arenabridge/<SID>/win/*`)
   - Provides interactive helper cmdlets (`Invoke-ZillionExec`, `Get-ZillionStatus`, `Start-ZillionWorker`, `Stop-ZillionWorker`)

## 🗂️ STRUCTURE
- `MEMORY_CORE.md` — canonical doctrine (public-safe, scrubbed; English v2.2 + 📖 READ MAP fast path)
- `docs/CHANGELOG.md` — historical version notes (archived verbatim from the core)
- `bridge/` — sandbox clients (phone_tun = tunnel + bootstrap + health_bundle · phone_mqtt = MQTT backup)
- `phone/` — phone stack: supervisor v4 · zg v1.2 (bootstrap op) · ph_beacon v3 · cf_retry v3 · fallback_retry · adb_watch v2 · worker v4.5.x · boot files
- `docs/` — manifest, code review, incident postmortem, update notes
- `apk/termux-boot_1000.apk` — Termux:Boot 0.8.1 (F-Droid, verified)

## 🔐 SECURITY MODEL
- All exec channels (tunnel + MQTT) = HMAC-SHA256 signed (envelope `{"d","h"}`)
- The only non-HMAC op = `bootstrap` (pre-key): sha256(passphrase) check + rate limit 5 fails / 900s
- Infra details here (SIDs, topics, stack) = not secret by design — integrity comes from HMAC, not confidentiality
- Private vault (with key): private repo + phone `_pack` + SD card
- Phone rebuild: see `docs/RESTORE_FILE_MANIFEST.md` and `phone/` contents
