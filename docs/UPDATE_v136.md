# UPDATE v1.3.6 — ZERO-ACTION RESTORE (2026-09-09)

Ang flow na ito ang pumapalit sa PAT/attachment flow ng v1.3.3–v1.3.5:

1. Boss (bagong chat, isang linya): `zillionCp <PASSPHRASE> https://github.com/limar01/zillion-restore`
2. Agent: `git clone https://github.com/limar01/zillion-restore.git` — PUBLIC, walang auth
3. Basahin ang MEMORY_CORE → GATE 0 (C1–C5) → LIST C
4. Beacon (`arenabridge/<SID>/ph/pres`, ts-fresh) → tunnel URL → `/ping`
5. `phone_tun.fetch_key(base, PASSPHRASE)` → key (zg v1.2 bootstrap: sha256 pass check + 5-fail/900s rate limit)
6. Isulat ang key sa `~/arenabridge/arenabridge.key` (600) → LIST C tuloy tuloy na

Notes:
- Ang core ay PUBLIC-SAFE: walang key, walang secrets (scrubbed v1.3.6).
- Private vault (kasama key): `limar01/tunnel-adb` (private) + phone `_pack` + SanDisk SD.
- Future pushes: deploy keys sa phone (`git@github-zr:`, `git@github-ta:`) — WALANG PAT.
- Kapos/na-leak ang passphrase: i-rotate via active session (bagong `_bootstrap.hash` + bagong restore line).
