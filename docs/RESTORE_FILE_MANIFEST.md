# 📦 RESTORE FILE MANIFEST — alin ang file saan (v1.3.2, 2026-09-09)
**Tanong ni Boss:** anong mga file ang dapat nasa agent sandbox at sa kanya (phone) para gumana ang restore?
**Prinsipyo:** ang restore ay **attachment-driven** — bagong chat + naka-attach na MEMORY_CORE = kumpleto na. Lahat ng iba ay derive o infrastructure.

---

## 🤖 A. AGENT SANDBOX (panig ko — bagong chat = bagong sandbox)

### Tanging entry point (kailangan BOSS ang mag-attach)
| File | Role |
|---|---|
| `uploads/MEMORY_CORE.md` (**v1.3.2**, 37,434B) | **ANG BUONG RESTORE ARTIFACT** — token, doctrines, GATE 0, embedded clients, key. Ito lang ang kailangan para mabuo ang lahat. |

### Ginagawa ng LIST C (hindi dadalhin — nireregla mula sa core)
| File | Source | Role |
|---|---|---|
| `arenabridge/arenabridge.key` | extract sa attachment (600, never echo) | HMAC signing |
| `bridge/__init__.py` · `mq_pc.py` · `tv_tun.py` · `phone_tun.py` · `phone_mqtt.py` | verbatim sa embedded sections ng core | mga client (tunnel primary / MQTT backup) |
| `pip install paho-mqtt` | — | MQTT dependency |

### Session convenience (opsyonal lang — hindi kritikal)
`zillion_phone_cf_url.txt` (cached URL — **beacon pa rin ang truth**) · `RESTORE_CODE_REVIEW.md` · `INCIDENT_20260909.md` · `zillion_phone/` (pulled copies) · `zillion_apk/termux-boot_1000.apk` (verified F-Droid build) · `phone_core_current.md` · `gen_v131.py` (scratch)

---

## 📱 B. PHONE (sandbox mo, Boss) — LIVE INFRASTRUCTURE (verified 01:32 PST)

### `~/zillion_pw/` — ang stack
| File | Version | Role |
|---|---|---|
| `supervisor.sh` | **v4** | 30s loop, atomic lock, nag-a-alsa ng lahat |
| `zg.py` | **v1.1** | HMAC gateway :8788 (ts + replay protection) |
| `ph_beacon.py` | **v3** | retained beacon + last-known-URL + healthy/url_age |
| `cf_retry.sh` | **v3** | cloudflared monitor (10s crash retry, 429 backoff, log rotation) |
| `fallback_retry.sh` | — | localhost.run backup tunnel |
| `start_all.sh` | — | entry point (idempotent) |
| `adb_watch.sh` | **v2** | ADB flapping auto-connect (full-range scan) |
| `cloudflared` | binary 37MB | quick-tunnel client |
| `_adb_ports.txt` | state | huling ADB port |
| *(logs: supervisor/cf/fallback/beacon/boot/zg)* | — | diagnostics (cf.log may rotation na) |

### `~/arenabridge/` — backup lane
| File | Role |
|---|---|
| `worker.py` (**v4.5**, AB_CMD_TIMEOUT=120) | MQTT exec worker (lane cp) |
| `arenabridge.key` | HMAC key (copy) |
| `approvals.json` | `outside_ok:true` (documented decision) |
| `workspace_mirror/` | put_file staging area |
| `activity.log` | audit log (trim na ngayon — walang auto-rotation pa, minor) |

### Boot chain + guards
| File | Role |
|---|---|
| `~/.termux/boot/start-zillion.sh` | Termux:Boot entry (sleep 30 → start_all) |
| `~/.profile` + `~/.bashrc` | auto-recover guards (F6, live-verified) |

### `~/zillion_pw/_pack/` — **PHONE REBUILD KIT** (refreshed 01:32, lahat SHA-match sa active)
`MEMORY_CORE.md` v1.3.2 · `arenabridge.key` · `cloudflared` · buong stack (supervisor v4, zg v1.1, beacon v3, cf_retry v3, fallback, start_all, adb_watch v2, worker v4.5) · `start-zillion.sh` · `profile.guard` · client copies (phone_tun/phone_mq/mq_pc/tv_tun) · `README.md` (rebuild order) · old cores (*.pre-* archive)

### Apps + Android settings (hindi files pero kailangan)
- **Termux** 0.119.0-beta.3 + **Termux:Boot** 0.8.1 (parehong F-Droid, sig `[7c3fcce]` match) + **Termux:API** — lahat opened once
- Wireless debugging ON (pairing persisted — walang re-pair) · deviceidle whitelist (3 packages) · *recommended: battery Unrestricted*

---

## 🔐 C. BOSS KEEPSAFE (off-device — panatilihin ang mga ito)
1. **MEMORY_CORE v1.3.2** — ang attachment file. Ito ang buong kaluluwa ng restore. *(copies: phone `_pack` + sandbox)*
2. **Recommended:** kopya ng buong `_pack/` folder sa laptop/cloud — kung mawala ang Termux data sa phone, ito ang buong rebuild kit (kasama key + cloudflared binary + core).
3. APKs — pwedeng uliting i-download sa F-Droid (same signing source requirement: lahat mula F-Droid).

## ⚠️ D. Mga katotohanan na dapat malaman
- **Ang key = access.** Naka-embed sa core attachment → kahit sino na may file na iyan ay may full exec sa phone. Ingatan ang kopya.
- **URL ay ephemeral** — beacon ang laging truth (may `ts` freshness check na).
- **Agent sandbox ay masisira pagkatapos ng session** — kaya ang core attachment ang tanging inaasahang dala. Huwag umasa sa `zillion_phone_cf_url.txt`.
- Bagong kitang nadiskubre habang ginagawa ang manifest: `activity.log` ng worker ay 19.9MB na (trim na sa 200KB; walang auto-rotation — maliit na future fix lang).
