import os, sys, json, time, uuid, hmac, hashlib, base64
import paho.mqtt.client as mqtt

SID = "53cf4a5803c91726b892e5d0785085c6"
KEY_PATH = os.path.expanduser("~/arenabridge/arenabridge.key")
KEY = open(KEY_PATH).read().strip() if os.path.exists(KEY_PATH) else ""
BROKER = "broker.emqx.io"
PORT = 1883

LANE = os.environ.get("ZILLION_LANE", "pc").strip()

if LANE == "cp":
    TOPIC_CMD = f"arenabridge/{SID}/cmd"
    TOPIC_RES = f"arenabridge/{SID}/res"
    TOPIC_PRES = f"arenabridge/{SID}/pres"
elif LANE == "win":
    TOPIC_CMD = f"arenabridge/{SID}/win/cmd"
    TOPIC_RES = f"arenabridge/{SID}/win/res"
    TOPIC_PRES = f"arenabridge/{SID}/win/pres"
else: # pc / omarchy
    TOPIC_CMD = f"arenabridge/{SID}/pc/cmd"
    TOPIC_RES = f"arenabridge/{SID}/pc/res"
    TOPIC_PRES = f"arenabridge/{SID}/pc/pres"

def sign_payload(data_dict):
    d_str = json.dumps(data_dict, separators=(',', ':'))
    h = hmac.new(KEY.encode(), d_str.encode(), hashlib.sha256).hexdigest()
    return json.dumps({"d": d_str, "h": h})

def verify_and_unpack(raw_bytes):
    try:
        raw = json.loads(raw_bytes.decode())
        d_str = raw.get("d", "")
        h = raw.get("h", "")
        if h:
            expected = hmac.new(KEY.encode(), d_str.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(h, expected):
                return None
        return json.loads(d_str)
    except:
        return None

def get_client(client_id=None):
    client_id = client_id or f"arena_agent_{uuid.uuid4().hex[:6]}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()
    return client, {"sid": SID, "key": KEY, "topic_cmd": TOPIC_CMD, "topic_res": TOPIC_RES, "topic_pres": TOPIC_PRES}

def req_res(client, cfg, payload, timeout=30):
    req_id = "req_" + uuid.uuid4().hex[:6]
    payload["id"] = req_id
    payload["ts"] = time.time()
    response_data = None
    done = False

    def on_message(c, u, msg):
        nonlocal done, response_data
        if msg.topic == cfg["topic_res"]:
            data = verify_and_unpack(msg.payload)
            if data and data.get("id") == req_id:
                response_data = data
                done = True

    client.subscribe(cfg["topic_res"], qos=1)
    client.on_message = on_message
    client.publish(cfg["topic_cmd"], sign_payload(payload), qos=1)
    
    start = time.time()
    while not done and (time.time() - start) < timeout:
        time.sleep(0.05)
        
    client.unsubscribe(cfg["topic_res"])
    if not done:
        return {"error": "timeout", "exit_code": -1, "output": "", "stderr": f"Timed out after {timeout}s"}
    return response_data

def exec_remote(cmd, timeout=30):
    client, cfg = get_client()
    res = req_res(client, cfg, {"op": "exec", "cmd": cmd}, timeout=timeout)
    client.loop_stop()
    client.disconnect()
    return res

def read_remote(path, timeout=15):
    client, cfg = get_client()
    res = req_res(client, cfg, {"op": "read", "path": path}, timeout=15)
    client.loop_stop()
    client.disconnect()
    return res

def get_screen_eyes(monitor="DVI-D-1", local_dest="/home/user/eyes_view.jpg", width=1400, quality=60):
    remote_png = "/tmp/eyes_capture.png"
    remote_jpg = "/tmp/eyes_capture.jpg"
    cmd = (
        "export XDG_RUNTIME_DIR=/run/user/1000 "
        "WAYLAND_DISPLAY=wayland-1 "
        "HYPRLAND_INSTANCE_SIGNATURE=$(ls /run/user/1000/hypr | head -n 1); "
        f"grim -o {monitor} {remote_png} && magick {remote_png} -resize {width}x -quality {quality} {remote_jpg}"
    )
    exec_res = exec_remote(cmd, timeout=20)
    res = read_remote(remote_jpg, timeout=15)
    if res and "b64" in res:
        data = base64.b64decode(res["b64"])
        with open(local_dest, "wb") as f:
            f.write(data)
        return {"ok": True, "path": local_dest, "size": len(data), "exec": exec_res}
    return {"ok": False, "error": (res.get("error") if res else "No response"), "exec": exec_res}
