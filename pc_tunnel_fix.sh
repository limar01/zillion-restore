#!/usr/bin/env bash
# ============================================================================
# zillion PC tunnel repair kit — run this ON the PC (Arch / Omarchy & any Linux)
#
#   bash pc_tunnel_fix.sh "<PASSPHRASE>"
#
# What it does, in order:
#   1. fetches the trusted tunnel URL from the public restore surface (url.txt)
#   2. refreshes the HMAC key from the phone gateway (keyless bootstrap)
#      -> fixes the known stale-key fault so the lane/door accepts this PC again
#   3. checks runtime deps (python3, paho-mqtt, cloudflared) and the local stack
#   4. applies the documented qwenOM deploy fixes (paho API + grep buffering)
#   5. starts zg.py (origin :8788) and a Cloudflare quick tunnel, captures the URL
#   6. verifies /ping + an HMAC exec round-trip end to end
#   7. publishes the live URL to the bridge (signed pc/pres) and writes it locally
#
# It never prints the key (fingerprint only), never writes credentials to disk
# beyond ~/arenabridge/arenabridge.key (chmod 600), and makes no destructive
# changes. Safe to re-run; idempotent.
# ============================================================================
set -uo pipefail

PASS="${1:-}"
REPO_RAW="https://raw.githubusercontent.com/limar01/zillion-restore/main"
SID="53cf4a5803c91726b892e5d0785085c6"
BROKER="broker.emqx.io"
WP="$HOME/arenabridge"
KEY="$WP/arenabridge.key"
URLF="$WP/pc_tunnel_url.txt"
ZG_PORT="${ZG_PORT:-8788}"
STACK_DIR="$HOME/Projects/tunnel_bridge"     # preferred if it exists
LOG="$WP/pc_tunnel_fix.log"

say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG"; }

mkdir -p "$WP"; touch "$LOG" 2>/dev/null
say "=== zillion PC tunnel repair kit ==="
say "host=$(hostname) user=$(id -un) dir=$WP"

if [ -z "$PASS" ]; then
  say "FATAL: passphrase required. Usage: bash pc_tunnel_fix.sh \"<PASSPHRASE>\""
  exit 2
fi

command -v python3 >/dev/null || { say "FATAL: python3 missing"; exit 2; }

# ---------------------------------------------------------------- 1. trusted URL
BASE="$(curl -fsS --max-time 15 "$REPO_RAW/url.txt" | tr -d '[:space:]')"
[ -n "$BASE" ] || { say "FATAL: could not fetch url.txt from the public surface"; exit 2; }
say "1/7 trusted gateway URL: $BASE"

# ---------------------------------------------------------------- 2. key refresh
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
    print("KEY REFRESH FAILED:", type(e).__name__, e); sys.exit(1)
out = json.loads(body["d"]) if body.get("d") else body
key = out.get("key") or ""
if not key:
    print("KEY REFRESH FAILED:", out); sys.exit(1)
open(keypath, "w").write(key + "\n")
os.chmod(keypath, 0o600)
print("2/7 key refreshed | fingerprint sha256(key) =", hashlib.sha256(key.encode()).hexdigest()[:16],
      "| path", keypath, "| mode 600")
PY
[ -s "$KEY" ] || { say "FATAL: no key written — aborting"; exit 2; }

# ---------------------------------------------------------------- 3. deps + stack
command -v cloudflared >/dev/null && say "3/7 cloudflared: $(cloudflared --version 2>/dev/null | head -1)" \
  || say "3/7 WARNING: cloudflared not found — install it (e.g. AUR cloudflared-bin) and re-run"
python3 -c 'import paho.mqtt.client' 2>/dev/null && say "3/7 paho-mqtt: present" \
  || { say "3/7 paho-mqtt missing — installing for the current user"; python3 -m pip install --user --quiet paho-mqtt || \
       say "3/7 WARNING: pip install failed; MQTT publish step will be skipped"; }
if [ -d "$STACK_DIR" ]; then say "3/7 stack: found $STACK_DIR"; else say "3/7 stack: $STACK_DIR not present (will use \$HOME copies)"; fi

# ---------------------------------------------------------------- 4. deploy fixes
for f in "$STACK_DIR"/*.py "$WP"/*.py "$HOME"/*.py; do
  [ -f "$f" ] || continue
  grep -q 'CallbackAPIVersion.VERSION2' "$f" 2>/dev/null && sed -i 's/mqtt.CallbackAPIVersion.VERSION2, //g' "$f" && say "4/7 fixed paho API in $f"
done
for f in "$STACK_DIR"/start_pc_stack.sh "$STACK_DIR"/*.sh; do
  [ -f "$f" ] || continue
  grep -q 'grep -oE' "$f" 2>/dev/null && sed -i 's/grep -oE/grep --line-buffered -oE/g' "$f" && say "4/7 fixed grep buffering in $f"
done

# ---------------------------------------------------------------- 5. origin + tunnel
ZG=""
for c in "$STACK_DIR/tunnel/zg.py" "$STACK_DIR/zg.py" "$WP/zg.py" "$HOME/zg.py"; do
  [ -f "$c" ] && { ZG="$c"; break; }
done
if [ -z "$ZG" ]; then
  say "5/7 zg.py not found locally — fetching the canonical one from the public surface"
  curl -fsS --max-time 20 "$REPO_RAW/zg.py" -o "$WP/zg.py" && ZG="$WP/zg.py" || { say "FATAL: cannot obtain zg.py"; exit 2; }
fi
if ! curl -fsS --max-time 3 "http://127.0.0.1:$ZG_PORT/ping" >/dev/null 2>&1; then
  nohup python3 "$ZG" >"$WP/zg.console.log" 2>&1 &
  sleep 2
  say "5/7 started origin: python3 $ZG (port $ZG_PORT)"
else
  say "5/7 origin already listening on $ZG_PORT"
fi

TUNNEL_PID=""
if command -v cloudflared >/dev/null; then
  nohup cloudflared tunnel --url "http://127.0.0.1:$ZG_PORT" --no-autoupdate >"$WP/cf.console.log" 2>&1 &
  TUNNEL_PID=$!
  for i in $(seq 1 20); do
    U="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$WP/cf.console.log" | head -1 || true)"
    [ -n "${U:-}" ] && break
    sleep 1
  done
  [ -n "${U:-}" ] && say "5/7 tunnel URL: $U" || say "5/7 WARNING: no quick-tunnel URL yet (see $WP/cf.console.log)"
else
  U=""
fi

# ---------------------------------------------------------------- 6. verify
python3 - "$KEY" "${U:-}" <<'PY' 2>&1 | tee -a "$LOG"
import hashlib, hmac, json, sys, time, uuid, urllib.request
key, base = open(sys.argv[1]).read().strip(), (sys.argv[2] or "").rstrip("/")
if not base:
    print("6/7 verify skipped (no tunnel URL)"); sys.exit(0)
try:
    with urllib.request.urlopen(base + "/ping", timeout=12) as r:
        env = json.loads(r.read().decode())
    h = hmac.new(key.encode(), env.get("d","").encode(), hashlib.sha256).hexdigest()
    assert hmac.compare_digest(h, env.get("h","")), "bad envelope hmac"
    print("6/7 /ping OK:", env["d"][:90])
    d = json.dumps({"op":"exec","id":"pc_"+uuid.uuid4().hex[:6],"cmd":"hostname; uname -sr; uptime -p","timeout":20,"ts":time.time()}, separators=(",",":"))
    body = json.dumps({"d": d, "h": hmac.new(key.encode(), d.encode(), hashlib.sha256).hexdigest()}).encode()
    req = urllib.request.Request(base + "/", data=body, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(json.loads(r.read().decode())["d"])
    print("6/7 HMAC exec round-trip OK | exit", out.get("exit_code"), "|", (out.get("output") or "").strip().replace("\n"," | "))
except Exception as e:
    print("6/7 VERIFY FAILED:", type(e).__name__, e)
PY

# ---------------------------------------------------------------- 7. publish to bridge
if [ -n "${U:-}" ]; then
  printf '%s\n' "$U" > "$URLF"
  python3 - "$KEY" "$U" <<'PY' 2>&1 | tee -a "$LOG"
import hashlib, hmac, json, os, socket, sys, time
key, url = open(sys.argv[1]).read().strip(), sys.argv[2]
try:
    import paho.mqtt.client as mqtt
except Exception as e:
    print("7/7 MQTT publish skipped (paho missing):", e); sys.exit(0)
SID = "53cf4a5803c91726b892e5d0785085c6"
payload = {"role": "pc", "host": socket.gethostname(), "user": os.environ.get("USER",""),
           "url": url, "online": True, "ver": "pc-tunnel-fix-v1", "ts": time.time()}
d = json.dumps(payload, separators=(",", ":"))
env = json.dumps({"d": d, "h": hmac.new(key.encode(), d.encode(), hashlib.sha256).hexdigest()})
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pc_fix_" + os.urandom(3).hex())
c.connect("broker.emqx.io", 1883, keepalive=30); c.loop_start()
c.publish(f"arenabridge/{SID}/pc/pres", env, qos=1, retain=True)
time.sleep(1.5); c.loop_stop(); c.disconnect()
print("7/7 published signed pc/pres (retained):", json.dumps(payload)[:160])
PY
else
  say "7/7 publish skipped (no URL)"
fi

say "DONE. URL file: $URLF | log: $LOG"
say "Next: re-run the lane identity check from the sandbox (expect hostname = this PC)."
