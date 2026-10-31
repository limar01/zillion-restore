# Zillion restore point — STATE/CURRENT

> **Auto-generated. Do not hand-edit.** Regenerate with `python3 ~/zillion_pw/state_snapshot.py --push`.
> Read this FIRST on restore (see READ MAP), then continue the last task. Snapshot is scrubbed: no keys, no passphrase.
> **Redacted for the public repo:** LAN addresses and commit subjects removed.

**Snapshot:** 2026-10-31 23:47:14 · **lane:** phone · **host:** SM-G975F / Android 16 · **uptime:** up 5 hours, 26 minutes

## Component state
| Component | State |
|---|---|
| Tunnel | LIVE — `https://see-luke-verse-comm.trycloudflare.com` (via url.txt(trusted)) |
| Bridge Worker | LIVE (pid 16991) |
| adb | LIVE — 127.0.0.1:38125 (1 transport(s)) |
| Deploy keys | zr=OK · ta=REJECTED · shopee=OK |

## LAST_TASK (what the next agent resumes)
**- Phone: `/data/data/com.termux/files/home/Projects/vector-us-vs-china`**

_source: /data/data/com.termux/files/home/zillion_pw/CURRENT_HANDOFF.md_

## Projects
- **shopeeaffiliate** · branch `master` · last `8814eb9 2026-10-17` · dirty 0 · ahead 0
  - newest: `tsconfig.json` (2026-10-17 23:14)

## Restore hint
1. clone repo → read `MEMORY_CORE.md` per READ MAP → **read this file**
2. bootstrap key, verify HMAC `/ping` against the tunnel above (it rotates — trust `url.txt` first)
3. verify worker + adb independently; only claim LIVE what you verified
4. resume: - Phone: `/data/data/com.termux/files/home/Projects/vector-us-vs-china`
