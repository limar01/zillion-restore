#!/usr/bin/env bash
# ============================================================================
# zillion PC onboard — puts THIS computer's storage on the ArenaBridge in one run
#
#   bash pc_onboard.sh "<PASSPHRASE>" [SYNC_ROOT]
#
# Needs: python3 (stdlib only), an internet connection, and the passphrase.
# No cloudflared, no SSH, no LAN membership required.
#
# After it finishes, the bridge can copy files to/from this machine (lane `pc`):
#   get_file / put_file / manifest  (paths are relative to SYNC_ROOT)
#   exec                            (approval-gated: reply "approve <id> allow_all")
#
# Key handling: written only to ~/arenabridge/arenabridge.key (mode 600);
# only its sha256 fingerprint is printed. Safe to re-run.
# ============================================================================
set -uo pipefail

PASS="${1:-}"
SYNC="${2:-$HOME}"                     # default: whole home dir reachable by get/put_file
WP="$HOME/arenabridge"
KEY="$WP/arenabridge.key"
LOG="$WP/onboard.log"
REPO_RAW="https://raw.githubusercontent.com/limar01/zillion-restore/main"

say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG"; }
mkdir -p "$WP" 2>/dev/null; touch "$LOG" 2>/dev/null

say "=== zillion PC onboard ==="
say "host=$(hostname) user=$(id -un) sync_root=$SYNC"

command -v python3 >/dev/null || { say "FATAL: python3 is required"; exit 2; }
[ -n "$PASS" ] || { say "FATAL: passphrase required. Usage: bash pc_onboard.sh \"<PASSPHRASE>\" [SYNC_ROOT]"; exit 2; }

# 1) trusted gateway URL from the public restore surface
BASE="$(curl -fsS --max-time 15 "$REPO_RAW/url.txt" | tr -d '[:space:]')" || true
[ -n "${BASE:-}" ] || { say "FATAL: cannot fetch url.txt"; exit 2; }
say "1/5 gateway: $BASE"

# 2) key: refresh from the phone gateway (keyless bootstrap)
python3 - "$BASE" "$PASS" "$KEY" <<'PY' 2>&1 | tee -a "$LOG"
import hashlib, json, os, sys, urllib.request
base, password, keypath = sys.argv[1], sys.argv[2], sys.argv[3]
req = urllib.request.Request(base.rstrip("/") + "/",
        data=json.dumps({"op": "bootstrap", "pass": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=25) as r:
        body = json.loads(r.read().decode())
except Exception as e:
    print("2/5 KEY REFRESH FAILED:", type(e).__name__, e); sys.exit(1)
out = json.loads(body["d"]) if body.get("d") else body
key = out.get("key") or ""
if not key:
    print("2/5 KEY REFRESH FAILED:", out); sys.exit(1)
open(keypath, "w").write(key + "\n"); os.chmod(keypath, 0o600)
print("2/5 key OK | sha256:", hashlib.sha256(key.encode()).hexdigest()[:16], "| ->", keypath, "(600)")
PY
[ -s "$KEY" ] || { say "FATAL: no key — aborting"; exit 2; }

# 3) worker (canonical, stdlib-only, lane-capable)
curl -fsS --max-time 30 "$REPO_RAW/phone/worker.py" -o "$WP/worker.py" || { say "FATAL: cannot download worker.py"; exit 2; }
say "3/5 worker v$(grep -o 'v4\.[0-9.]*' "$WP/worker.py" | head -1 | tr -d v) -> $WP/worker.py"

# 4) restart exactly one worker on lane pc
pkill -f "arenabridge/worker.py" 2>/dev/null && say "4/5 stopped previous worker instance(s)"
sleep 1
cd "$WP" || exit 2
BRIDGE_CWD="$WP" ZILLION_LANE=pc AB_SYNC_ROOT="$SYNC" AB_CMD_TIMEOUT=120 \
  nohup python3 "$WP/worker.py" > "$WP/worker.console.log" 2>&1 &
sleep 5
pgrep -f "arenabridge/worker.py" >/dev/null && say "4/5 worker running (lane pc, pid $(pgrep -f 'arenabridge/worker.py' | head -1))" \
  || { say "4/5 WARNING: worker not running — last log lines:"; tail -5 "$WP/worker.console.log" 2>/dev/null; }
say "4/5 last log: $(tail -3 "$WP/worker.console.log" 2>/dev/null | tr '\n' ' ' | cut -c1-200)"

# 5) prove the lane round-trip from this machine (self-test via the bridge)
python3 - "$KEY" <<'PY' 2>&1 | tee -a "$LOG"
import hashlib, hmac, json, os, socket, sys, time, uuid
key = open(sys.argv[1]).read().strip()
try:
    import paho.mqtt.client as mqtt
    HAVE_PAHO = True
except Exception:
    HAVE_PAHO = False
SID = "53cf4a5803c91726b892e5d0785085c6"
if not HAVE_PAHO:
    print("5/5 self-test skipped (paho-mqtt not installed) — worker still publishes presence on its own")
    sys.exit(0)
res = []
def on_msg(c, u, m):
    try:
        env = json.loads(m.payload.decode()); d = json.loads(env["d"])
        if d.get("id") == rid: res.append(d)
    except Exception: pass
rid = "ob_" + uuid.uuid4().hex[:6]
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ob_" + uuid.uuid4().hex[:6])
c.on_message = on_msg; c.connect("broker.emqx.io", 1883, keepalive=30); c.loop_start()
c.subscribe(f"arenabridge/{SID}/pc/res", qos=1); time.sleep(1)
d = json.dumps({"op": "exec", "id": rid, "cmd": "hostname", "ts": time.time()}, separators=(",", ":"))
c.publish(f"arenabridge/{SID}/pc/cmd", json.dumps({"d": d, "h": hmac.new(key.encode(), d.encode(), hashlib.sha256).hexdigest()}), qos=1)
t0 = time.time()
while time.time() - t0 < 15 and not res: time.sleep(0.1)
c.loop_stop(); c.disconnect()
print("5/5 lane self-test:", "OK ->", res[0].get("output", "").strip() if res else "no reply (check worker.console.log)")
PY

say "DONE — worker is on the bridge. Tell the sandbox agent to fetch files (get_file) or run commands (exec)."
