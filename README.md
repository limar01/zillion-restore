# ⚡ ZILLION RESTORE — public restore surface

Public repo ito (by design) — **walang secrets dito**. Ang HMAC key ay HINDI kasama;
ina-deliver ito ng passphrase-protected bootstrap op ng phone (zg v1.2).

## 📥 RESTORE (agent, bagong chat)
1. Si Boss ay magpapaste ng isang linya: `zillionCp <PASSPHRASE> https://github.com/limar01/zillion-restore`
2. `git clone https://github.com/limar01/zillion-restore.git` (walang auth)
3. `MEMORY_CORE.md` = doctrine — GATE 0 (C1–C5 capability check) bago ang lahat, tapos LIST C
4. Key: `phone_tun.fetch_key(base, PASSPHRASE)` — keyless bootstrap (rate-limited)
5. Sundin ang LIST C — walang modification, raw evidence lahat

## 🗂️ ESTRUKTURA
- `MEMORY_CORE.md` — canonical doctrine (public-safe, scrubbed)
- `bridge/` — sandbox clients (phone_tun = tunnel+bootstrap · phone_mqtt = MQTT backup)
- `phone/` — phone stack: supervisor v4 · zg v1.2 (bootstrap op) · ph_beacon v3 · cf_retry v3 · fallback_retry · adb_watch v2 · worker v4.5.1 · boot files
- `docs/` — manifest, code review, incident postmortem, update notes
- `apk/termux-boot_1000.apk` — Termux:Boot 0.8.1 (F-Droid, verified)

## 🔐 SECURITY MODEL
- Lahat ng exec channels (tunnel + MQTT) = HMAC-SHA256 signed (envelope `{"d","h"}`)
- Ang tanging hindi-HMAC op = `bootstrap` (pre-key ito): sha256(passphrase) check + rate limit 5 fail / 900s
- Infra details dito (SIDs, topics, stack) = hindi secret by design — integrity ang HMAC, hindi confidentiality
- Private vault (may key): private repo + phone `_pack` + SD card
- Rebuild ng phone: tingnan ang `docs/RESTORE_FILE_MANIFEST.md` at `phone/` contents
