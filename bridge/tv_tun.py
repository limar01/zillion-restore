"""TV box Cloudflare tunnel client (HMAC JSON). Exec path = HTTPS, never MQTT worker."""
import json, time, hmac, hashlib, urllib.request, os, uuid

KEY_PATH = os.path.expanduser("~/arenabridge/arenabridge.key")
KEY = open(KEY_PATH).read().strip() if os.path.exists(KEY_PATH) else ""
LAST_URL_FILE = os.path.expanduser("~/zillion_tv_cf_url.txt")
TV_SID = "3b6d57b5465bd22238186fb32850e569"
BROKER, BPORT = "broker.emqx.io", 1883
T_PRES = f"arenabridge/{TV_SID}/tv/pres"

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
        open(LAST_URL_FILE, "w").write(u + "\n")
    return u

def load_saved_url():
    try:
        return open(LAST_URL_FILE).read().strip().rstrip("/")
    except Exception:
        return ""

def discover_url_mqtt(timeout=8):
    try:
        import paho.mqtt.client as mqtt
    except Exception:
        return ""
    found = {"u": ""}
    def on_msg(c, u, msg):
        try:
            data = _unpack(msg.payload.decode() if isinstance(msg.payload, bytes) else msg.payload)
        except Exception:
            try:
                import json as _j
                raw = _j.loads(msg.payload.decode())
                data = _j.loads(raw.get("d", "{}"))
            except Exception:
                return
        if data.get("url"):
            found["u"] = data["url"]
    try:
        cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="tvurl_" + uuid.uuid4().hex[:6])
    except Exception:
        cl = mqtt.Client(client_id="tvurl_" + uuid.uuid4().hex[:6])
    cl.on_message = on_msg
    cl.connect(BROKER, BPORT, keepalive=30)
    cl.subscribe(T_PRES, qos=0)
    cl.loop_start()
    t0 = time.time()
    while time.time() - t0 < timeout and not found["u"]:
        time.sleep(0.1)
    cl.loop_stop()
    cl.disconnect()
    return save_url(found["u"]) if found["u"] else ""

def ping_url(base, timeout=8):
    base = (base or "").strip().rstrip("/")
    if not base:
        return False
    try:
        with urllib.request.urlopen(base + "/ping", timeout=timeout) as r:
            raw = r.read().decode()
        data = _unpack(raw)
        return data.get("ok") is True or data.get("role") == "tv"
    except Exception:
        return False

def resolve_url(hint=""):
    for cand in (hint, load_saved_url()):
        if ping_url(cand):
            return save_url(cand)
    u = discover_url_mqtt(8)
    if ping_url(u):
        return save_url(u)
    return ""

def exec_tv(cmd, timeout=30, base=None):
    base = (base or resolve_url()).rstrip("/")
    if not base:
        return {"error": "no_tv_tunnel_url", "exit_code": -1, "output": "", "stderr": ""}
    payload = {"op": "exec", "id": "t_" + uuid.uuid4().hex[:6], "cmd": cmd, "timeout": timeout}
    req = urllib.request.Request(base + "/", data=_env(payload), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout + 10) as r:
        return _unpack(r.read().decode())
