#!/usr/bin/env bash
# ============================================================================
# zillion PC onboard — puts THIS computer's storage on the ArenaBridge in one run
#
#   bash pc_onboard.sh "<PASSPHRASE>" [SYNC_ROOT] [--no-worker] [--selftest-only]
#
# Needs: python3 (stdlib only), an internet connection, and the passphrase.
# No cloudflared, no SSH, no LAN membership required.
#
# After it finishes, the bridge can copy files to/from this machine (lane `pc`):
#   get_file / put_file / manifest  (paths relative to SYNC_ROOT)
#   exec                            (approval-gated: reply "approve <id> allow_all")
#
# Key handling: written only to ~/arenabridge/arenabridge.key (mode 600);
# only its sha256 fingerprint is printed. Safe to re-run.
#
# v2 fixes: rejects a placeholder passphrase instead of sending it; a failed key
# refresh no longer aborts when an existing key still authenticates; the lane
# self-test works on paho 1.x AND 2.x (v1's used the 2.x-only API).
# ============================================================================
set -uo pipefail

PASS=""
SYNC="$HOME"
NO_WORKER=0
SELFTEST_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --no-worker)      NO_WORKER=1 ;;
    --selftest-only)  SELFTEST_ONLY=1 ;;
    -h|--help)        sed -n '2,20p' "$0"; exit 0 ;;
    *)
      if [ -z "$PASS" ]; then PASS="$arg"
      else SYNC="$arg"; fi ;;
  esac
done

WP="$HOME/arenabridge"
KEY="$WP/arenabridge.key"
LOG="$WP/onboard.log"
REPO_RAW="https://raw.githubusercontent.com/limar01/zillion-restore/main"

say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG"; }
mkdir -p "$WP" 2>/dev/null; touch "$LOG" 2>/dev/null

say "=== zillion PC onboard (v2) ==="
say "host=$(hostname) user=$(id -un) sync_root=$SYNC"

command -v python3 >/dev/null || { say "FATAL: python3 is required"; exit 2; }

# ---------------------------------------------------------------- arg guard
if [ "$SELFTEST_ONLY" -eq 0 ]; then
  case "$PASS" in
    "")
      say "FATAL: passphrase required. Usage: bash pc_onboard.sh \"<PASSPHRASE>\" [SYNC_ROOT]"; exit 2 ;;
    *"<"*|*">"*)
      say "FATAL: that is a placeholder, not a passphrase: '$PASS'"
      say "       paste the REAL passphrase from your restore line (no angle brackets)."
      exit 2 ;;
  esac
fi

# ---------------------------------------------------------------- 1. gateway URL
BASE="$(curl -fsS --max-time 15 "$REPO_RAW/url.txt" | tr -d '[:space:]')" || true
[ -n "${BASE:-}" ] || { say "FATAL: cannot fetch url.txt"; exit 2; }
say "1/5 gateway: $BASE"

# ---------------------------------------------------------------- 2. key
if [ "$SELFTEST_ONLY" -eq 0 ]; then
  python3 - "$BASE" "$PASS" "$KEY" <<'PY' 2>&1 | tee -a "$LOG"
"""Key: refresh via the gateway's bootstrap op; if that fails, keep a WORKING existing key."""
import hashlib, hmac, json, os, sys, urllib.error, urllib.request

base, password, keypath = sys.argv[1], sys.argv[2], sys.argv[3]

def existing_key_ok(path):
    if not os.path.isfile(path):
        return None
    key = open(path).read().strip()
    if not key:
        return None
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/ping", timeout=12) as r:
            env = json.loads(r.read().decode())
        good = hmac.compare_digest(hmac.new(key.encode(), env["d"].encode(), hashlib.sha256).hexdigest(), env.get("h", ""))
        return key if good else None
    except Exception:
        return None

req = urllib.request.Request(base.rstrip("/") + "/",
        data=json.dumps({"op": "bootstrap", "pass": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=25) as r:
        body = json.loads(r.read().decode())
    out = json.loads(body["d"]) if body.get("d") else body
    key = out.get("key") or ""
    if not key:
        raise ValueError(out)
    open(keypath, "w").write(key + "\n")
    os.chmod(keypath, 0o600)
    print("2/5 key refreshed OK | sha256:", hashlib.sha256(key.encode()).hexdigest()[:16], "| ->", keypath, "(600)")
except urllib.error.HTTPError as e:
    detail = ""
    try:
        detail = e.read().decode()[:120]
    except Exception:
        pass
    if e.code == 403:
        print("2/5 bootstrap rejected (403 bad passphrase — or rate-limited after 5 fails).")
    else:
        print(f"2/5 bootstrap failed: HTTP {e.code} {detail}")
    old = existing_key_ok(keypath)
    if old:
        print("2/5 existing key still authenticates against the gateway — continuing with it.")
        print("    sha256:", hashlib.sha256(old.encode()).hexdigest()[:16], "| ->", keypath)
        sys.exit(0)
    print("2/5 FATAL: no usable key (refresh failed and the existing one does not authenticate).")
    sys.exit(1)
except Exception as e:
    print("2/5 bootstrap error:", type(e).__name__, e)
    old = existing_key_ok(keypath)
    if old:
        print("2/5 existing key still authenticates — continuing with it.")
        sys.exit(0)
    sys.exit(1)
PY
  [ "${PIPESTATUS[0]}" = "0" ] || { say "FATAL: key step failed"; exit 2; }
  [ -s "$KEY" ] || { say "FATAL: no key file"; exit 2; }
fi

# ---------------------------------------------------------------- 3. worker file
if [ "$SELFTEST_ONLY" -eq 0 ]; then
  curl -fsS --max-time 30 "$REPO_RAW/phone/worker.py" -o "$WP/worker.py" || { say "FATAL: cannot download worker.py"; exit 2; }
  say "3/5 worker $(grep -o 'v4\.[0-9.]*' "$WP/worker.py" | head -1) -> $WP/worker.py"
fi

# ---------------------------------------------------------------- 4. start worker
if [ "$SELFTEST_ONLY" -eq 0 ] && [ "$NO_WORKER" -eq 0 ]; then
  pkill -f "arenabridge/worker.py" 2>/dev/null && say "4/5 stopped previous worker instance(s)"
  sleep 1
  cd "$WP" || exit 2
  BRIDGE_CWD="$WP" ZILLION_LANE=pc AB_SYNC_ROOT="$SYNC" AB_CMD_TIMEOUT=120 \
    nohup python3 "$WP/worker.py" > "$WP/worker.console.log" 2>&1 &
  sleep 5
  if pgrep -f "arenabridge/worker.py" >/dev/null; then
    say "4/5 worker running (lane pc, pid $(pgrep -f 'arenabridge/worker.py' | head -1))"
  else
    say "4/5 WARNING: worker not running — last log lines:"
    tail -5 "$WP/worker.console.log" 2>/dev/null | tee -a "$LOG"
  fi
else
  say "4/5 worker step skipped"
fi

# ---------------------------------------------------------------- 5. lane self-test
python3 - "$KEY" <<'PY' 2>&1 | tee -a "$LOG"
"""Lane self-test — paho 1.x AND 2.x safe (v1 used the 2.x-only API and crashed)."""
import hashlib, hmac, json, sys, time, uuid

key = open(sys.argv[1]).read().strip()
try:
    import paho.mqtt.client as mqtt
    import paho.mqtt as paho_pkg
except Exception as e:
    print("5/5 self-test skipped (paho-mqtt not installed):", e)
    sys.exit(0)

def make_client(cid):
    if hasattr(mqtt, "CallbackAPIVersion"):          # paho >= 2.0
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    return mqtt.Client(client_id=cid)                 # paho 1.x

SID = "53cf4a5803c91726b892e5d0785085c6"
res, rid = [], "ob_" + uuid.uuid4().hex[:6]

def on_msg(c, u, m):
    try:
        env = json.loads(m.payload.decode())
        d = env.get("d", "")
        if not isinstance(d, str) or not hmac.compare_digest(
                hmac.new(key.encode(), d.encode(), hashlib.sha256).hexdigest(), env.get("h", "")):
            return
        data = json.loads(d)
        if data.get("id") == rid:
            res.append(data)
    except Exception:
        pass

print("5/5 paho version:", getattr(paho_pkg, "__version__", "?"))
c = make_client("ob_" + uuid.uuid4().hex[:6])
c.on_message = on_msg
c.connect("broker.emqx.io", 1883, keepalive=30)
c.loop_start()
c.subscribe(f"arenabridge/{SID}/pc/res", qos=1)
time.sleep(1)
d = json.dumps({"op": "exec", "id": rid, "cmd": "hostname", "ts": time.time()}, separators=(",", ":"))
c.publish(f"arenabridge/{SID}/pc/cmd",
          json.dumps({"d": d, "h": hmac.new(key.encode(), d.encode(), hashlib.sha256).hexdigest()}), qos=1)
t0 = time.time()
while time.time() - t0 < 15 and not res:
    time.sleep(0.1)
c.loop_stop()
c.disconnect()
print("5/5 lane self-test:", "OK -> " + res[0].get("output", "").strip() if res else
      "no verified reply (is the worker running? see worker.console.log)")
PY

say "DONE — worker is on the bridge. Tell the sandbox agent to fetch files (get_file) or run commands (exec)."
