#!/usr/bin/env python3
# zillion_gateway.py — Zillion Cloudflare-Tunnel gateway (HMAC-protected JSON API)
# 2026-09-07: sandbox <-> phone via Cloudflare tunnel, replaces MQTT as primary channel.
# Same HMAC-SHA256 envelope: {"d": <compact json>, "h": hmac-sha256(key, d)}.
# 2026-09-09 v1.1 (CR F5): + ts freshness (±300s) + seen-id replay cache (256) +
#   exec timeout clamp 1..600s. Ops: ping, health (GET+POST) · exec · read. Stdlib only.
# 2026-09-09 v1.2: + BOOTSTRAP op — keyless key delivery para sa blank-sandbox restore.
#   Plain-JSON request (walang {d,h} envelope): {"op":"bootstrap","pass":"..."}
#   Proteksyon: sha256(pass) == ~/zillion_pw/_bootstrap.hash + rate limit (5 fail = 900s lock).
#   Ito ang TANGING hindi-HMAC op — deliberately, dahil pre-key ito.
import json, time, hmac, hashlib, base64, os, sys, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

START = time.time()
PORT = int(os.environ.get("ZG_PORT", "8788"))
KEY_PATH = os.path.expanduser("~/arenabridge/arenabridge.key")
KEY = open(KEY_PATH).read().strip() if os.path.exists(KEY_PATH) else ""
MAX_OUT = 1 << 20
ALLOWED = {"ping", "exec", "read", "health"}
HOSTNAME = os.uname().nodename
_SEEN = {}          # F5: replay cache — id -> ts (bounded 256, FIFO evict)
_BOOT = {"fails": 0, "lock_until": 0.0}   # v1.2: bootstrap rate limiter
BOOT_HASH_PATH = os.path.expanduser("~/zillion_pw/_bootstrap.hash")

def _bootstrap(passw):
    # v1.2: keyless key delivery — passphrase-protected, rate-limited.
    import hashlib as _h
    now = time.time()
    if now < _BOOT["lock_until"]:
        return {"op": "bootstrap", "ok": False,
                "error": "locked; try again in %ds" % int(_BOOT["lock_until"] - now)}, 429
    try:
        want = open(BOOT_HASH_PATH).read().strip()
    except Exception:
        return {"op": "bootstrap", "ok": False, "error": "bootstrap disabled"}, 404
    if passw and _h.sha256(passw.encode()).hexdigest() == want:
        _BOOT["fails"] = 0
        return {"op": "bootstrap", "ok": True, "key": KEY}, 200
    _BOOT["fails"] += 1
    if _BOOT["fails"] >= 5:
        _BOOT["lock_until"] = now + 900
        _BOOT["fails"] = 0
        return {"op": "bootstrap", "ok": False, "error": "locked 900s"}, 429
    return {"op": "bootstrap", "ok": False, "error": "bad pass"}, 403

def sign(s):
    return hmac.new(KEY.encode(), s.encode(), hashlib.sha256).hexdigest()

def envelope(obj):
    d = json.dumps(obj, separators=(',', ':'))
    return json.dumps({"d": d, "h": sign(d)}).encode()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("zg: " + (fmt % args) + "\n")

    def _reply(self, obj, code=200):
        body = envelope(obj)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/ping", "/health"):
            self._reply({"op": self.path.strip("/"), "ok": True, "ts": time.time(),
                         "host": HOSTNAME, "up": round(time.time() - START, 1)})
        else:
            self._reply({"error": "not found"}, 404)

    def do_POST(self):
        rid = ""
        try:
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n > (1 << 20):
                self._reply({"error": "payload too large"}, 413); return
            raw = self.rfile.read(n) or b"{}"
            env = json.loads(raw)
            # v1.2: bootstrap = plain JSON (pre-key), lahat ng iba = HMAC envelope
            if "h" not in env and env.get("op") == "bootstrap":
                out, code = _bootstrap(str(env.get("pass", "")))
                self._reply(out, code); return
            d, h = env.get("d", ""), env.get("h", "")
            if not h or not hmac.compare_digest(sign(d), h):
                self._reply({"error": "bad signature"}, 403); return
            req = json.loads(d)
            # F5: freshness + replay protection
            ts = req.get("ts")
            if not isinstance(ts, (int, float)) or abs(time.time() - ts) > 300:
                self._reply({"error": "bad or stale ts"}, 401); return
            rid = str(req.get("id", ""))
            if rid:
                if rid in _SEEN:
                    self._reply({"id": rid, "error": "replay blocked"}, 409); return
                if len(_SEEN) >= 256:
                    _SEEN.pop(next(iter(_SEEN)))
                _SEEN[rid] = time.time()
            op = req.get("op")
            if op not in ALLOWED:
                self._reply({"id": rid, "error": "unknown op"}, 400); return
            if op == "ping":
                out = {"id": rid, "op": "ping", "ok": True, "ts": time.time(), "host": HOSTNAME}
            elif op == "health":
                out = {"id": rid, "op": "health", "ts": time.time(), "host": HOSTNAME,
                       "pid": os.getpid(), "up": round(time.time() - START, 1)}
            elif op == "exec":
                cmd = str(req.get("cmd", ""))
                if len(cmd) > (1 << 20):
                    self._reply({"id": rid, "error": "cmd too large"}, 413); return
                t = req.get("timeout", 30)
                try:
                    t = int(t)
                except (TypeError, ValueError):
                    t = 30
                t = max(1, min(t, 600))   # F5: clamp
                p = subprocess.run(["sh", "-c", cmd], capture_output=True, timeout=t)
                out = {"id": rid, "op": "exec", "exit_code": p.returncode,
                       "output": p.stdout.decode(errors="replace")[:MAX_OUT],
                       "stderr": p.stderr.decode(errors="replace")[:MAX_OUT]}
            else:  # read
                path = str(req.get("path", ""))
                if len(path) > 512 or path.startswith("-"):
                    self._reply({"id": rid, "error": "bad path"}, 400); return
                with open(path, "rb") as f:
                    data = f.read(8 << 20)
                out = {"id": rid, "op": "read", "path": path,
                       "b64": base64.b64encode(data).decode()}
            self._reply(out)
        except subprocess.TimeoutExpired:
            self._reply({"id": rid, "error": "exec timeout"})
        except Exception as e:
            try:
                self._reply({"id": rid, "error": repr(e)}, 500)
            except Exception:
                pass

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"zillion_gateway: {HOSTNAME} listening on 127.0.0.1:{PORT} (key={'OK' if KEY else 'MISSING'})", flush=True)
    srv.serve_forever()
