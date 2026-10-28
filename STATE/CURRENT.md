# Zillion restore point — STATE/CURRENT

> **Auto-generated. Do not hand-edit.** Regenerate with `python3 ~/zillion_pw/state_snapshot.py --push`.
> Read this FIRST on restore (see READ MAP), then continue the last task. Snapshot is scrubbed: no keys, no passphrase.

**Snapshot:** 2026-10-28 15:56:56 · **lane:** phone · **host:** SM-G975F / Android 16 · **uptime:** up 19 hours, 15 minutes

## Component state
| Component | State |
|---|---|
| Tunnel | LIVE — `https://5df3faf4268362.lhr.life` (via url.txt(trusted)) |
| Bridge Worker | LIVE (pid 15702) |
| adb | LIVE — 127.0.0.1:36785, 192.168.100.50:36785 |
| Deploy keys | zr=REJECTED · ta=REJECTED · shopee=OK: Hi limar01/shopeeaffiliate! You've successfully authenticated, but GitHub does not provide shell access. |

## LAST_TASK (what the next agent resumes)
**shopeeaffiliate — newest file tsconfig.json (2026-10-17 23:14)**

_source: newest-mtime — **inferred from file mtimes, not a declared handoff**_

## Projects
- **shopeeaffiliate** · branch `master` · last `8814eb9 2026-10-17 feat(google_flow): 5-beat hook formula (47s/5 clips), picker-search cast attach, Veo 3.1-Lite pin` · dirty 0 · ahead 0
  - newest: `tsconfig.json` (2026-10-17 23:14)

## Restore hint
1. clone repo → read `MEMORY_CORE.md` per READ MAP → **read this file**
2. bootstrap key, verify HMAC `/ping` against the tunnel above (it rotates — trust `url.txt` first)
3. verify worker + adb independently; only claim LIVE what you verified
4. resume: shopeeaffiliate — newest file tsconfig.json (2026-10-17 23:14)
