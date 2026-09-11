"""Sandbox helper: HMAC 'read' op over the phone tunnel (zg.py).
Usage: python3 tun_read.py <phone_path> <local_dest>
Max ~8MB per read (server-side cap). For screenshots/dumps only.
"""
import json, sys, os, time, uuid, hmac, hashlib, urllib.request, base64

KEY = open(os.path.expanduser("~/arenabridge/arenabridge.key")).read().strip()
BASE = open(os.path.expanduser("~/zillion_phone_cf_url.txt")).read().strip().rstrip("/")

def _sign(s):
    return hmac.new(KEY.encode(), s.encode(), hashlib.sha256).hexdigest()

def read_remote(path, timeout=60):
    d = json.dumps({"op": "read", "id": "rd_" + uuid.uuid4().hex[:6],
                    "path": path, "timeout": timeout, "ts": time.time()},
                   separators=(",", ":"))
    body = json.dumps({"d": d, "h": _sign(d)}).encode()
    req = urllib.request.Request(BASE + "/", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout + 10) as r:
        env = json.loads(r.read().decode())
    dd, h = env.get("d", ""), env.get("h", "")
    if h and not hmac.compare_digest(_sign(dd), h):
        raise ValueError("bad hmac")
    out = json.loads(dd)
    if out.get("error"):
        raise RuntimeError(out.get("error"))
    return base64.b64decode(out["b64"])

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    data = read_remote(src)
    open(dst, "wb").write(data)
    print(f"OK {len(data)} bytes -> {dst}")
