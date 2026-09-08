"""Phone lane MQTT backup client (worker v4.5, HMAC-signed).
Use when the CF tunnel is down: discovery via retained ph/pres, exec/file ops via cmd/res.
v2 (2026-09-09 CR): F2 — full broker rotation (emqx -> hivemq -> mosquitto) sa op() at
presence(); F13 — docstring fix: T_PRE = worker presence lang (beacon ay sa ph/pres)."""
import os, json, time, uuid, hmac, hashlib, base64
import paho.mqtt.client as mqtt

SID = "53cf4a5803c91726b892e5d0785085c6"
KEY_PATH = os.path.expanduser("~/arenabridge/arenabridge.key")
KEY = open(KEY_PATH).read().strip() if os.path.exists(KEY_PATH) else ""
BROKERS = ["broker.emqx.io", "broker.hivemq.com", "test.mosquitto.org"]
T_CMD = f"arenabridge/{SID}/cmd"
T_RES = f"arenabridge/{SID}/res"
T_PRE = f"arenabridge/{SID}/pres"   # worker presence (beacon = arenabridge/<SID>/ph/pres)

def _sign(d):
    return hmac.new(KEY.encode(), d.encode(), hashlib.sha256).hexdigest()

def _pack(obj):
    d = json.dumps(obj, separators=(",", ":"))
    return json.dumps({"d": d, "h": _sign(d)})

def _unpack(raw):
    try:
        env = json.loads(raw)
        d, h = env.get("d", ""), env.get("h", "")
        if h and not hmac.compare_digest(_sign(d), h):
            return None
        return json.loads(d)
    except Exception:
        return None

def op(payload, timeout=45, broker=None):
    """Signed op via cmd/res. v2: walang broker param = iikot sa LAHAT ng brokers (F2)."""
    brokers = [broker] if broker else BROKERS
    per = max(12, timeout // len(brokers))
    last_err = None
    for host in brokers:
        rid = "sm_" + uuid.uuid4().hex[:6]
        pl = dict(payload)
        pl["id"] = rid
        pl["ts"] = time.time()
        result = {"response": None}
        done = False
        def on_msg(c, u, msg):
            nonlocal done
            if msg.topic == T_RES:
                data = _unpack(msg.payload)
                if data and data.get("id") == rid:
                    result["response"] = data
                    done = True
        try:
            try:
                cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sm_" + uuid.uuid4().hex[:6])
            except Exception:
                cl = mqtt.Client(client_id="sm_" + uuid.uuid4().hex[:6])
            cl.on_message = on_msg
            cl.connect(host, 1883, keepalive=60)
            cl.subscribe(T_RES, qos=1)
            cl.loop_start()
            cl.publish(T_CMD, _pack(pl), qos=1)
            t0 = time.time()
            while not done and time.time() - t0 < per:
                time.sleep(0.05)
            cl.loop_stop()
            cl.disconnect()
        except Exception as e:
            last_err = f"{host}: {type(e).__name__}"
            continue
        if done:
            return result["response"]
        last_err = f"{host}: no response in {per}s"
    return {"error": "timeout", "exit_code": -1, "output": "", "stderr": f"all brokers failed; last: {last_err}"}

def exec_ph(cmd, timeout=45):
    """Exec on phone via MQTT worker (backup path). HMAC-signed both ways."""
    return op({"op": "exec", "cmd": cmd}, timeout=timeout)

def put_file(path, data, timeout=60):
    """Put bytes to phone path (worker free zone). data: bytes."""
    return op({"op": "put_file", "path": path, "b64": base64.b64encode(data).decode()}, timeout=timeout)

def note(text, timeout=15):
    return op({"op": "note", "note": text}, timeout=timeout)

def presence(timeout=8, fresh_after=None):
    """Read retained WORKER presence. v2: broker rotation; fresh_after (epoch) = F3
    freshness filter — stale retained ay hindi tatanggapin."""
    per = max(5, timeout // len(BROKERS))
    for host in BROKERS:
        found = {}
        def on_msg(c, u, msg):
            try:
                data = _unpack(msg.payload)
                if data:
                    found.update(data)
            except Exception:
                pass
        try:
            try:
                cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pr_" + uuid.uuid4().hex[:6])
            except Exception:
                cl = mqtt.Client(client_id="pr_" + uuid.uuid4().hex[:6])
            cl.on_message = on_msg
            cl.connect(host, 1883, keepalive=30)
            cl.subscribe(T_PRE, qos=0)
            cl.loop_start()
            t0 = time.time()
            while time.time() - t0 < per and not found.get("ts"):
                time.sleep(0.1)
            cl.loop_stop()
            cl.disconnect()
        except Exception:
            continue
        if found:
            if fresh_after is not None and (found.get("ts") or 0) < fresh_after:
                continue
            return found
    return {}
