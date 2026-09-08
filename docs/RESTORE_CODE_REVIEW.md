# 🔍 CODE REVIEW — Zillion Restore Process
**Scope:** MEMORY_CORE v1.3.1 protocol + buong restore chain (10 files, live-pulled from phone 2026-09-09 ~01:20 PST)
**Method:** source review ng aktwal na deployed code (hindi memorya) + today's live evidence (reboot test, kill test, ADB flapping)
**Overall: SOLID ang architecture — 3 P1 availability bugs, 4 P2 robustness gaps, hygiene items. Lahat may concrete fix.**

---

## Severity legend
🔴 **P1** = maaaring mag-fail ang restore mismo · 🟠 **P2** = humina ang recovery/backup lane · 🟡 **P3** = hygiene/cosmetic

## Findings summary

| # | Sev | Component | Issue |
|---|-----|-----------|-------|
| F1 | 🔴 | ph_beacon.py | Retained URL na **tinatanggal ng empty string** kapag patay ang parehong tunnel |
| F2 | 🔴 | bridge/phone_mqtt.py | **Walang broker rotation** sa client (worker nagro-rotate, client hindi) |
| F3 | 🔴 | bridge/phone_tun.py | `discover_mqtt()` **walang ts-freshness check** (retained trap — nangyari na sa akin) |
| F4 | 🟠 | worker.py | **Single-thread exec, CMD_TIMEOUT=600s** — isang hung command = 10-min dead backup lane + walang presence |
| F5 | 🟠 | zg.py | **Walang replay protection / ts freshness** (worker may 1-slot cache; zg wala) + unbounded exec timeout |
| F6 | 🟠 | ~/.bashrc guard | **Maaaring INERT** — Termux login shell ay hindi gumagamit ng .bashrc kung walang sourcing (verified: /etc/profile walang bashrc reference) |
| F7 | 🟠 | logs | **cf.log unbounded growth** (`>>` append; ~4MB/day worst case sa reconnect loops) |
| F8 | 🟡 | worker.py | `outside_ok: true` = **approval engine OFF** (verified sa approvals.json; 0 LOCKED lines sa buong worker.log) + SYSTEM_OPS ay **Windows-only** list (walang rm -rf/dd/pm) |
| F9 | 🟡 | ph_beacon.py | adb() stderr ay nagpo-pollute ng beacon.log (daemon messages) + substring `"device" in ln` match |
| F10 | 🟡 | adb_watch.sh | scan range 20000–60000 lang (pwedeng < 20000 ang port) |
| F11 | 🟡 | worker.py | version mismatch: `info ver 4.5` vs `act() "ver 4.4"` |
| F12 | 🟡 | supervisor.sh | duplicate-start noong 21:05 + 21:07 (evidence sa supervisor.log) — guard hindi tumama sa ibang invocation form; start_zg 4s curl = kill-churn risk ng healthy zg sa load |
| F13 | 🟡 | docs | phone_mqtt.presence() docstring mali ("worker + beacon both publish here" — beacon ay sa `ph/pres`, hindi `pres`) |

---

## 🔴 P1 — Detailed + patches

### F1: Beacon empty-URL overwrite (restore killer)
**File:** `ph_beacon.py` L24–26 (`url()` returns `""` kapag walang healthy) + L41 (publishes it retained)
**Impact:** Kapag nasa 429-window ang trycloudflare AT nagre-restart ang fallback (20s gap), ang beacon ay nagpu-publish ng `url:""` **retained** — papalit sa dating magaling na URL. Ang agent ay walang makukuhang URL kahit babalik ang tunnel after seconds. **Na-witness ko ito ngayon** (PH_BEACON `{}` kanina).
**Fix (ph_beacon v3):**
```python
LAST_URL = ""
def url():
    global LAST_URL
    cf = found(CF, r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    fb = found(FB, r"https://[a-zA-Z0-9-]+\.lhr\.life")
    for u in (cf, fb):
        if healthy(u):
            LAST_URL = u
            return u
    return LAST_URL  # retain last-known; add "stale" flag sa publish
# sa publish: {"url": url(), "healthy": <bool>, ...}
```
Ang `resolve_url` naman ay laging nagpi-ping bago gamitin — kaya safe ang "last-known + ping" pattern.

### F2: Backup client walang broker rotation
**File:** `bridge/phone_mqtt.py` — `op()` defaults `BROKERS[0]` (emqx) lang.
**Impact:** Kapag emqx ang bumagsak, dead ang backup lane ng client kahit ang worker ay kumikilos na via hivemq/mosquitto. Kalaban ito ng layunin ng "backup lane" (dapat mas reliable ang recovery path).
**Fix:** loop sa 3 brokers sa `op()` at `presence()`; try next kapag timeout/connect error (worker rotation = emqx→hivemq→mosquitto, sundan).

### F3: Retained-pres trap hindi naka-enforce sa client code
**File:** `bridge/phone_tun.py` — `discover_mqtt()` tinatanggap kahit anong retained message.
**Impact:** Ako mismo ang nabiktima ngayon sa reboot test ("MQTT ALIVE T+26s" — stale retained pala). Doktrina na sa core na "ts freshness mandatory" pero ang code ay hindi pumipilit.
**Fix:** `discover_mqtt(timeout=8, fresh_after=None)` — kung may `fresh_after` (epoch), hintayin lang ang `ts > fresh_after`. Gamitin sa lahat ng restore flows.

---

## 🟠 P2 — Detailed

### F4: Worker single-thread + 600s timeout
**File:** `worker.py` L224 (`CMD_TIMEOUT=600`) + `main()` (on_cmd → run() blocking, heartbeat sa parehong thread)
**Impact:** Isang `adb logcat` / interactive / hung command = 10 minuto walang response at walang presence → mukhang dead phone. Backup lane ang worker — hindi pwedeng sarili niyang command ang pumatay sa kanya.
**Fix (minimal, walang refactor):** sa `supervisor.sh` start_worker line: `env ZILLION_LANE=cp AB_CMD_TIMEOUT=120 python3 ...` (phone context: 120s sapat sa repair ops; configurable pa rin via env). Threading = future work.

### F5: zg.py replay/freshness
**File:** `zg.py` `do_POST` — HMAC-valid ang tanging check; walang ts, walang seen-id.
**Impact:** Ang isang nakuha/nag-replay na signed envelope ay valid habang buhay (theoretical — kailangan ng traffic capture sa CF/localhost.run edge o key leak). Plus: `timeout` mula sa request ay walang clamp (pwedeng 86400).
**Fix:** payload ts check (`|now−ts| ≤ 60s`) + maliit na seen-id set (huling 256) + `t = max(1, min(t, 600))`.

### F6: .bashrc guard — maaaring hindi tumatakbo
**Evidence:** `/etc/profile` walang bashrc sourcing; Termux login shell ay nagbabasa ng `.profile`/`.bash_profile`. Ang guard ko ay nasa `.bashrc` lang (187 bytes = puro guard).
**Impact:** Ang Plan-B rescue (bukas Termux → auto-recover) ay maaaring inert. Hindi na-test ngayon dahil gumana ang Termux:Boot (hindi na-trigger ang guard).
**Fix:** i-duplicate ang guard sa `~/.profile` (idempotent) + isang beses na physical test ni Boss (bukas Termux nang patay ang supervisor → dapat bumangon).

### F7: Log growth
**File:** `cf_retry.sh` (`>> cf.log`), cf.log = 28KB/~10min sa reconnect storms.
**Fix:** sa bawat ATTEMPT: `mv cf.log cf.log.1 2>/dev/null; : > cf.log` (keep 1 generation). Idagdag din sa supervisor ang simple size check (`[ $(wc -c < cf.log) -gt 5000000 ] && : > cf.log`).

---

## 🟡 P3 (quick list)
- **F8:** I-document sa core: `outside_ok:true` = accepted state (kailangan ng repair ops na may `~` paths); kung gusto mo ng real gating sa phone lane, dagdagan ang SYSTEM_OPS ng Linux/Android patterns (`rm -rf`, `dd `, `mkfs`, `pm uninstall`, `adb reboot`) — pero NOTE: haharangin nito ang repair ops mismo kaya `outside_ok` ay dapat manatiling true + agent discipline (Boss GO) ang primary gate. **Decision mo ito, Boss.**
- **F9:** beacon adb(): `subprocess.check_output([...], stderr=subprocess.DEVNULL)` + exact `awk '$2=="device"'` matching.
- **F10:** adb_watch scan 1024–65535 ( threaded, mabilis naman).
- **F11:** i-sync ang version string (4.5 pareho).
- **F12:** supervisor start line: idagdag ang `bash` invocation sa pgrep pattern; start_zg: 2 retries bago kill (iwas churn sa load spikes).
- **F13:** itama ang docstring (T_PRE = worker pres lamang; beacon = `ph/pres`).

---

## ✅ What's GOOD (worth keeping as-is)
1. **HMAC everywhere, compare_digest** — lahat ng lanes (zg, worker, beacon, clients) ay signed pareho; unsigned/bad-sig = blocked (worker: verified sa code).
2. **worker never-silent dispatcher** — kahit mag-crash ang on_cmd, may error reply pabalik (v4.3 addition, maganda).
3. **fallback_retry.sh log truncation bago restart** (`: > fallback.log`) — hindi kinukuha ang stale URL. Magandang detail.
4. **supervisor anchored pgrep guards** (`^python3 .*/path$`) — tama ang dedup na pattern per service.
5. **zg.py size caps + op allowlist + ThreadingHTTPServer** — concurrent exec, bounded memory.
6. **worker safe_path + MAX_FILE 2MB** sa file ops; `mkdir -p` na tama.
7. **Boot chain** — verified live end-to-end ngayong araw (reboot test 00:43→00:46).
8. **Replay cache sa worker** (1-slot) — client retries ay hindi nagdo-double-execute.

## 🔐 Security & trust model (honest notes)
- **Hindi kumpidensyal ang lanes:** trycloudflare/lhr.life proxies (CF edge, localhost.run server) ay KAYANG makabasa ng commands/outputs — HMAC ang nagpro-protekta ng *integrity* (walang makaka-forge), hindi ng confidentiality. **Aligned ito sa doktrina na "never echo keys"** — panatilihin: walang secrets sa commands/outputs.
- **Key distribution:** ang HMAC key ay nasa MEMORY_CORE attachment mismo → kahit sino na may chat transcript = full exec sa phone. Ito ang designed architecture mo (token = access); accepted, pero isa lang itong kopya ng buong puso ng access — ingatan ang attachment.
- **zg read op:** unrestricted path (kahit anong file na readable ng u0_a395, kasama ang mismong key) — same trust tier as exec (may key ka na = pwede mo nang i-cat), walang dagdag na exposure.

## 🎯 Recommended GO list (priority order)
1. **P1 bundle:** ph_beacon v3 (F1) + phone_mqtt rotation (F2) + phone_tun fresh_after (F3) — core v1.3.2 + redeploy + isang kill-test para patunayin ang F1 fix.
2. **P2 quick wins:** AB_CMD_TIMEOUT=120 (F4), .profile guard (F6), cf.log rotation (F7) — 3 one-liners, isang deploy.
3. zg replay/ts (F5) — mas malikot (dg maingat na patch + test).
4. P3 hygiene — sabay-sabay sa susunod na core release.
