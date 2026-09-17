"""Phone Cloudflare tunnel + ADB — v2.2.0 (English, restore-speed optimized).
Exec = HTTPS HMAC-SHA256 envelope via zg.py. MQTT ph/pres = URL+adb discovery ONLY.
History: v1.3.2 ts + retained-trap guard · v1.3.6 fetch_key() keyless bootstrap ·
v2.2.0 code-review optimizations:
  - resolve_fast(): trusted-URL-first (url.txt hint -> saved -> seed); MQTT beacon
    consulted ONLY when all static candidates fail. No more MQTT-first 15s window
    on the hot path (was the main restore latency source).
  - health_bundle(): ONE Cloudflare round trip returns host/date/uptime/model,
    worker liveness (anchored pgrep — KILL-LOOP rule), adb device list, and
    deploy-key ssh -T results. Replaces ~6 sequential per-exec round trips.
  - adb_ready(): QUICK by default (adb devices + previously discovered ports +
    optional beacon port). The 30000-60000 deep scan is opt-in (deep=True) and
    documented as CF-524-prone (poll, never sleep long inside one payload).
  - ping_url default timeout 8s -> 6s; discover_mqtt default window 8s.
v2.3.0:
  - status(): ONE-CALL quick health check for the `-status`/`-fix` parameters
    (resolve_fast + health_bundle + tunnel_ok verdict). Read-only.
"""
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

def ping_url(base, timeout=6):
    """HMAC-verified /ping. Pre-key this CANNOT verify (no key yet) — treat as
    liveness-only until the key exists; trusted origin = url.txt from the repo."""
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
    """Beacon discovery (post-key use per TRUSTED-URL doctrine; retained-trap guard:
    when fresh_after (epoch) is set, stale retained pres is not accepted)."""
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
        time.sleep(0.1)
    cl.loop_stop()
    cl.disconnect()
    if fresh_after is not None and (found.get("ts") or 0) < fresh_after:
        return {}
    return found

def resolve_fast(hint="", mqtt_timeout=10):
    """v2.2.0 PRIMARY RESOLVER — trusted-URL-first.
    Order: hint (url.txt from public repo, TRUSTED channel) -> saved last URL -> seed.
    HMAC-ping each; beacon MQTT only when every static candidate fails (post-key).
    Returns (url, info) — info = beacon payload when consulted, else {}."""
    for c in (hint, load_saved(), SEED):
        if c and ping_url(c):
            return save_url(c), {}
    info = discover_mqtt(mqtt_timeout)
    u = info.get("url")
    if u and ping_url(u):
        return save_url(u), info
    return "", info

def resolve_url(hint=""):
    """Legacy resolver (beacon-first) — kept for compatibility; resolve_fast preferred."""
    info = discover_mqtt(8)
    cands = [hint, info.get("url"), load_saved(), SEED]
    for c in cands:
        if ping_url(c):
            return save_url(c), info
    return "", info

def resolve_url_long(timeout=150):
    """Extended discovery — loops beacon+ping until a healthy URL appears or timeout.
    Use ONLY post-reboot / when resolve_fast already failed (beacon needs boot time)."""
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
    """KEYLESS BOOTSTRAP — plain-JSON POST (no HMAC: pre-key by design).
    Phone-side protection: sha256(pass) vs _bootstrap.hash + rate limit 5-fail/900s.
    Send the passphrase ONLY to the trusted url.txt origin — never to beacon-derived URLs."""
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
        base, _ = resolve_fast(load_saved())
    base = (base or "").rstrip("/")
    if not base:
        return {"error": "no_phone_tunnel_url", "exit_code": -1, "output": ""}
    payload = {"op": "exec", "id": "p_" + uuid.uuid4().hex[:6], "cmd": cmd, "timeout": timeout, "ts": time.time()}
    req = urllib.request.Request(base + "/", data=_env(payload), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout + 10) as r:
        return _unpack(r.read().decode())

def health_bundle(base=None, timeout=60):
    """v2.2.0: ONE Cloudflare round trip — full restore verification.
    Returns dict keys: host/date/up/model/android · worker (anchored pgrep line or
    NONE) · adb (device lines, '|' separated) · key_zr / key_ta (ssh -T first lines —
    expect 'Hi limar01/...!', exit 1 is normal) · _exit/_error meta. All read-only.
    Keep the phone-side script SHORT: exec payloads must stay <90s (CF 524)."""
    if not base:
        base = load_saved()
    cmd = (
        'echo "HOST=$(hostname)"; echo "DATE=$(date)"; echo "UP=$(uptime)"; '
        'echo "MODEL=$(getprop ro.product.model 2>/dev/null)"; '
        'echo "ANDROID=$(getprop ro.build.version.release 2>/dev/null)"; '
        'W=$(pgrep -fl worker.py 2>/dev/null | grep -v pgrep | head -3 | tr "\n" "|"); echo "WORKER=${W:-NONE}"; '
        'echo "ADB=$(adb devices 2>/dev/null | awk \'NR>1 && NF\' | tr "\n" "|")"; '
        'echo "KEY_ZR=$(ssh -o ConnectTimeout=8 -T github-zr 2>&1 | head -1)"; '
        'echo "KEY_TA=$(ssh -o ConnectTimeout=8 -T github-ta 2>&1 | head -1)"'
    )
    r = exec_ph(cmd, timeout=timeout, base=base)
    out = {}
    for line in (r.get("output", "") or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip().lower()] = v
    out["_exit"] = r.get("exit_code")
    out["_error"] = r.get("error")
    return out

def status(base_hint="", timeout=60):
    """v2.3.0: ONE-CALL quick health check for the `-status` / `-fix` parameters
    and the `status` session shortcut. Read-only: resolve_fast(hint) then one
    health_bundle round trip. Returns the bundle dict plus `url` + `tunnel_ok`
    (True when the HMAC exec round trip itself succeeded). Compose the exact
    -status final line from: url/tunnel_ok · up · worker · adb · key_zr/key_ta."""
    url, info = resolve_fast(hint=base_hint or load_saved())
    if not url:
        return {"url": "", "tunnel_ok": False, "info": info, "_error": "no_phone_tunnel_url"}
    hb = health_bundle(base=url, timeout=timeout)
    hb["url"] = url
    hb["tunnel_ok"] = (hb.get("_exit") == 0 and not hb.get("_error"))
    return hb

def adb_ready(deep=False, timeout=45, extra_ports=""):
    """v2.2.0: QUICK by default. (1) adb start-server + devices — a 'device' entry
    means READY (disconnect 'offline' zombies per doctrine). (2) Try previously
    discovered ports (~/zillion_pw/_adb_ports.txt) + extra_ports (e.g. beacon adb
    field). deep=True = legacy 30000-60000 full scan — slow on a loaded phone and
    can outlive the ~90s CF window; the scan keeps running phone-side, so poll
    'adb devices' afterwards instead of sleeping inside one payload.
    /tmp is PROHIBITED (shell-owned) — scan results go to ~/zillion_pw/_adb_ports.txt."""
    if not deep:
        cmd = (
            "adb start-server >/dev/null 2>&1\n"
            "for p in $(cat ~/zillion_pw/_adb_ports.txt 2>/dev/null) " + (extra_ports or "") + "; do "
            "adb connect 127.0.0.1:$p >/dev/null 2>&1; done\n"
            "adb devices -l\n"
        )
        return exec_ph(cmd, timeout=timeout)
    cmd = r"""
adb start-server >/dev/null 2>&1
if adb devices | grep -qE 'device$'; then adb devices -l; exit 0; fi
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
    return exec_ph(cmd, timeout=max(timeout, 120))
