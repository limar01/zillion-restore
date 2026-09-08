"""Phone Cloudflare tunnel + ADB. Exec = HTTPS HMAC, not MQTT worker.
MQTT ph/pres = URL+adb discovery only.
v1.3.2: exec payload may ts (zg v1.1) · discover_mqtt(fresh_after=) retained-trap guard (F3).
v1.3.6: + fetch_key() — keyless bootstrap (passphrase-protected) para sa blank-sandbox restore."""
import json, time, hmac, hashlib, urllib.request, os, uuid

KEY_PATH = os.path.expanduser("~/arenabridge/arenabridge.key")
KEY = open(KEY_PATH).read().strip() if os.path.exists(KEY_PATH) else ""
LAST = os.path.expanduser("~/zillion_phone_cf_url.txt")
SID = "53cf4a5803c91726b892e5d0785085c6"
BROKER, BPORT = "broker.emqx.io", 1883
T_PRES = f"arenabridge/{SID}/ph/pres"
SEED = "https://wearing-quotations-der-asset.trycloudflare.com"

def _sign(s):
    return hmac.new(KEY.encode(), s.encode(), hashlib.sha256).hexdigest()

def _env(obj):
    d = json.dumps(obj, separators=(",", ":"))
    return json.dumps({"d": d, "h": _sign(d)}).encode()

def _unpack(raw):
    env = json.loads(raw)
    d, h = env.get("d", ""), env.get("h", "")
    if h and not hmac.compare_digest(_sign(d), h):
        raise ValueError("bad hmac")
    return json.loads(d)

def save_url(u):
    u = (u or "").strip().rstrip("/")
    if u:
        open(LAST, "w").write(u + "\n")
    return u

def load_saved():
    try:
        return open(LAST).read().strip().rstrip("/")
    except Exception:
        return SEED

def ping_url(base, timeout=8):
    base = (base or "").strip().rstrip("/")
    if not base:
        return False
    try:
        with urllib.request.urlopen(base + "/ping", timeout=timeout) as r:
            data = _unpack(r.read().decode())
        return data.get("ok") is True
    except Exception:
        return False

def discover_mqtt(timeout=8, fresh_after=None):
    """v1.3.2 (CR F3): fresh_after (epoch) — kung nakatakda, ang stale retained
    pres ay HINDI tinatanggap (hintayin ang sariwang publish)."""
    try:
        import paho.mqtt.client as mqtt
    except Exception:
        return {}
    found = {}
    def on_msg(c, u, msg):
        try:
            found.update(_unpack(msg.payload.decode() if isinstance(msg.payload, bytes) else msg.payload))
        except Exception:
            try:
                raw = json.loads(msg.payload.decode())
                found.update(json.loads(raw.get("d", "{}")))
            except Exception:
                pass
    try:
        cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="phurl_" + uuid.uuid4().hex[:6])
    except Exception:
        cl = mqtt.Client(client_id="phurl_" + uuid.uuid4().hex[:6])
    cl.on_message = on_msg
    cl.connect(BROKER, BPORT, keepalive=30)
    cl.subscribe(T_PRES, qos=0)
    cl.loop_start()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if found.get("url"):
            if fresh_after is None or (found.get("ts") or 0) >= fresh_after:
                break
            # stale retained — keep waiting for a fresh publish
        time.sleep(0.1)
    cl.loop_stop()
    cl.disconnect()
    if fresh_after is not None and (found.get("ts") or 0) < fresh_after:
        return {}
    return found

def resolve_url(hint=""):
    info = discover_mqtt(8)
    cands = [hint, info.get("url"), load_saved(), SEED]
    for c in cands:
        if ping_url(c):
            return save_url(c), info
    return "", info

def resolve_url_long(timeout=150):
    """v1.3.1: extended restore discovery — loops beacon+ping until healthy URL or timeout.
    Use on restore after phone reboot (beacon needs boot time to publish a fresh URL)."""
    t0 = time.time()
    last_info = {}
    while time.time() - t0 < timeout:
        info = discover_mqtt(15)
        if info:
            last_info = info
        for c in (info.get("url"), load_saved(), SEED):
            if c and ping_url(c, 8):
                return save_url(c), info
        time.sleep(5)
    return "", last_info

def fetch_key(base, passphrase, timeout=15):
    """v1.3.6: KEYLESS BOOTSTRAP — plain-JSON POST (walang HMAC: pre-key ito).
    Proteksyon: passphrase (sha256 vs _bootstrap.hash sa phone) + rate limit 5/900s sa zg v1.2.
    Success = 200 + {"key": "..."} sa loob ng signed envelope (i-unwrap ang 'd')."""
    payload = json.dumps({"op": "bootstrap", "pass": passphrase}).encode()
    req = urllib.request.Request((base or "").rstrip("/") + "/", data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode())
    d = body.get("d")
    out = json.loads(d) if d else body
    return out.get("key") or ""

def exec_ph(cmd, timeout=30, base=None):
    if not base:
        base, _ = resolve_url()
    base = (base or "").rstrip("/")
    if not base:
        return {"error": "no_phone_tunnel_url", "exit_code": -1, "output": ""}
    payload = {"op": "exec", "id": "p_" + uuid.uuid4().hex[:6], "cmd": cmd, "timeout": timeout, "ts": time.time()}
    req = urllib.request.Request(base + "/", data=_env(payload), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout + 10) as r:
        return _unpack(r.read().decode())

def adb_ready(timeout=45):
    """Ensure adb device via tunnel exec. Returns exec result.
    v1.3.1: scan writes ~/zillion_pw/_adb_ports.txt (/tmp is shell-owned → PermissionError on exec user),
    range 30000-60000. Note: a connected 'offline' port is usually NOT adb — verify with devices list."""
    cmd = r"""
adb start-server >/dev/null 2>&1
if adb devices | grep -qE 'device$'; then adb devices -l; exit 0; fi
# reconnect last ports
for p in $(adb devices | awk -F: '/127.0.0.1/{print $2}' | awk '{print $1}'); do adb connect 127.0.0.1:$p >/dev/null 2>&1; done
python3 - << 'P'
import socket, os
opens=[]
for p in range(30000,60001):
    s=socket.socket(); s.settimeout(0.02)
    try:
        s.connect(('127.0.0.1',p)); opens.append(p)
    except Exception:
        pass
    finally:
        try: s.close()
        except Exception: pass
d=os.path.expanduser('~/zillion_pw'); os.makedirs(d, exist_ok=True)
open(os.path.join(d,'_adb_ports.txt'),'w').write(' '.join(map(str,opens)))
print('scan', opens)
P
for p in $(cat ~/zillion_pw/_adb_ports.txt 2>/dev/null); do adb connect 127.0.0.1:$p >/dev/null 2>&1; done
sleep 3
adb devices -l
"""
    return exec_ph(cmd, timeout=timeout)
