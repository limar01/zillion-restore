# Zillion restore point — STATE/CURRENT

> **Auto-generated. Do not hand-edit.** Regenerate with `python3 ~/zillion_pw/state_snapshot.py --push`.
> Read this FIRST on restore (see READ MAP), then continue the last task. Snapshot is scrubbed: no keys, no passphrase.
> **Redacted for the public repo:** LAN addresses and commit subjects removed.

**Snapshot:** 2026-11-25 01:00:12 · **lane:** phone · **host:** SM-G975F / Android 16 · **uptime:** up 25 minutes

## Component state
| Component | State |
|---|---|
| Tunnel | DOWN — `-` (via none) |
| Bridge Worker | LIVE (pid 20180) |
| adb | DOWN — no devices (0 transport(s)) |
| Deploy keys | zr=OK · ta=OK · shopee=OK |

## LAST_TASK (what the next agent resumes)
**- Phone: `/data/data/com.termux/files/home/Projects/workspace/arena-android-client`**

_source: /data/data/com.termux/files/home/zillion_pw/CURRENT_HANDOFF.md_

## Projects
- **arena-android-client** · branch `-` · last `` · dirty 0 · ahead 0
  - newest: `docs/HANDOFF.md` (2026-11-01 09:09)
- **rea-scratch** · branch `-` · last `` · dirty 0 · ahead 0
  - newest: `rea/website/requirements.txt` (2026-11-01 07:45)
- **references** · branch `-` · last `` · dirty 0 · ahead 0
  - newest: `rea-review/rea-mcp-analysis.md` (2026-11-04 05:04)
- **shopeeaffiliate** · branch `master` · last `2910f1f 2026-11-21` · dirty 12 · ahead 0
  - newest: `tools/feed_photo_post.py` (2026-11-24 10:33)
- **zillion-doctrine** · branch `-` · last `` · dirty 0 · ahead 0
  - newest: `LAST_CHECKPOINT_RECEIPT.json` (2026-11-04 10:27)

## Restore hint
1. clone repo → read `MEMORY_CORE.md` per READ MAP → **read this file**
2. bootstrap key, verify HMAC `/ping` against the tunnel above (it rotates — trust `url.txt` first)
3. verify worker + adb independently; only claim LIVE what you verified
4. resume: - Phone: `/data/data/com.termux/files/home/Projects/workspace/arena-android-client`
