# ============================================================
# ArenaBridge WORKER v4 (SYNC + APPROVALS) -- stdlib only
# Ops: exec / put_file / get_file / manifest / del_file / approve / pending / policy
# Policy: D:\arenabridge subtree = free; outside paths & system ops need approval.
# Decisions persist in approvals.json (allow / allow_all / deny).
# ============================================================
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# mqtt_minimal.py -- minimal MQTT 3.1.1 client, pure python stdlib
# supports: CONNECT (clean session + last will), SUBSCRIBE, PUBLISH qos0
# (+retain), PINGREQ keepalive, background dispatch. No external deps.
import hashlib
import hmac as _hmac
import json
import secrets as _secrets
import select
import socket
import struct
import time


def _enc_len(n):
    out = b""
    while True:
        b = n % 128
        n //= 128
        if n:
            b |= 0x80
        out += bytes([b])
        if not n:
            return out


def _str(s):
    if isinstance(s, str):
        s = s.encode("utf-8")
    return struct.pack(">H", len(s)) + s


# ---- tiny signed-message protocol on top of any transport ----
def mkmsg(key, obj):
    body = json.dumps(obj, separators=(",", ":"))
    mac = _hmac.new(key.encode(), body.encode(), hashlib.sha256).hexdigest()
    return json.dumps({"d": body, "h": mac}, separators=(",", ":"))


def readmsg(key, raw):
    # returns dict if signature valid, else None
    try:
        env = json.loads(raw)
        body, mac = env["d"], env["h"]
        good = _hmac.compare_digest(
            _hmac.new(key.encode(), body.encode(), hashlib.sha256).hexdigest(),
            mac)
        return json.loads(body) if good else None
    except Exception:
        return None


class MiniMQTT:
    def __init__(self, host, port=1883, client_id=None, keepalive=60):
        self.host = host
        self.port = port
        self.cid = client_id or ("mm-" + _secrets.token_hex(5))
        self.keepalive = keepalive
        self.sock = None
        self.cbs = {}
        self.buf = b""
        self.last_ping = 0.0
        self.ping_since = None
        self.mid = 1

    # ---- connection ----
    def connect(self, timeout=15, will_topic=None, will_payload="",
                will_retain=True):
        self.sock = socket.create_connection((self.host, self.port),
                                             timeout=timeout)
        self.sock.settimeout(None)
        flags = 0x02  # clean session
        if will_topic is not None:
            flags |= 0x04 | (0x20 if will_retain else 0)
        vh = _str("MQTT") + bytes([4, flags]) + struct.pack(
            ">H", self.keepalive)
        payload = _str(self.cid)
        if will_topic is not None:
            payload += _str(will_topic) + _str(will_payload)
        pkt = b"\x10" + _enc_len(len(vh) + len(payload)) + vh + payload
        self.sock.sendall(pkt)
        self.buf = b""
        self.last_ping = time.time()
        # wait CONNACK (READ from socket, then parse)
        t0 = time.time()
        while time.time() - t0 < timeout:
            r, _, _ = select.select([self.sock], [], [], 0.3)
            if r:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("closed while waiting CONNACK")
                self.buf += chunk
            pkt = self._parse_one()
            if pkt is not None and pkt[0] == 2:
                body = pkt[1]
                if len(body) >= 2 and body[1] != 0:
                    raise ConnectionError("broker refused connection code=%d" % body[1])
                return True
        raise ConnectionError("no CONNACK from broker")

    def close(self):
        try:
            self.sock.sendall(b"\xe0\x00")
            self.sock.close()
        except Exception:
            pass

    # ---- pub/sub ----
    def subscribe(self, topic, cb):
        body = struct.pack(">H", self.mid) + _str(topic) + b"\x00"
        self.mid += 1
        self.sock.sendall(b"\x82" + _enc_len(len(body)) + body)
        self.cbs[topic] = cb

    def publish(self, topic, payload, retain=False):
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        body = _str(topic) + payload
        hdr = bytes([0x30 | (1 if retain else 0)])
        self.sock.sendall(hdr + _enc_len(len(body)) + body)

    # ---- read/dispatch ----
    def _parse_one(self):
        if len(self.buf) < 2:
            return None
        b0 = self.buf[0]
        # remaining length varint
        n = 0
        mul = 1
        i = 1
        while True:
            if i >= len(self.buf):
                return None
            b = self.buf[i]
            n += (b & 0x7F) * mul
            mul *= 128
            i += 1
            if not (b & 0x80):
                break
            if i > 4:
                raise ConnectionError("bad remaining length")
        total = i + n
        if len(self.buf) < total:
            return None
        body = self.buf[i:total]
        self.buf = self.buf[total:]
        t = b0 >> 4
        if t == 3:  # PUBLISH qos0
            tl = struct.unpack(">H", body[:2])[0]
            topic = body[2:2 + tl].decode("utf-8", "replace")
            pl = body[2 + tl:]
            return (t, (topic, pl))
        return (t, body)

    def loop(self, timeout=1.0):
        # returns True if any packet was dispatched
        moved = False
        try:
            r, _, _ = select.select([self.sock], [], [], timeout)
            if r:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("socket closed by broker")
                self.buf += chunk
        except socket.timeout:
            pass
        while True:
            pkt = self._parse_one()
            if pkt is None:
                break
            t, data = pkt
            moved = True
            if t == 3:
                topic, pl = data
                cb = self.cbs.get(topic)
                if cb:
                    try:
                        cb(pl.decode("utf-8", "replace"))
                    except Exception:
                        pass
            elif t == 13:
                self.last_ping = time.time()
                self.ping_since = None
        # keepalive + v4.5 zombie-link detector:
        # PAGHATID ng PINGREQ; kung walang PINGRESP sa loob ng 20s,
        # ang linya ay zombie -- i-raise para mag-rotate/reconnect ang caller.
        now = time.time()
        if now - self.last_ping > self.keepalive * 0.7:
            if self.ping_since is None:
                self.sock.sendall(b"\xc0\x00")
                self.ping_since = now
            elif now - self.ping_since > 20:
                raise ConnectionError("zombie link: walang PINGRESP sa 20s")
        elif self.ping_since is not None:
            self.ping_since = None
            self.last_ping = time.time()
        return moved


BROKERS = ["broker.emqx.io", "broker.hivemq.com", "test.mosquitto.org"]
BASE = "arenabridge/53cf4a5803c91726b892e5d0785085c6"
T_CMD = BASE + "/cmd"
T_RES = BASE + "/res"
T_PRE = BASE + "/pres"
_KEY_PATH = os.path.expanduser("~/arenabridge/arenabridge.key")
KEY = open(_KEY_PATH).read().strip() if os.path.exists(_KEY_PATH) else ""
WORKDIR = os.environ.get("BRIDGE_CWD") or "/data/data/com.termux/files/home/arenabridge"
SYNC_ROOT = Path(os.environ.get("AB_SYNC_ROOT") or os.path.join(WORKDIR, "workspace_mirror"))
APPROVALS_FILE = Path(WORKDIR) / "approvals.json"
CMD_TIMEOUT = int(os.environ.get("AB_CMD_TIMEOUT", "600"))
MAXLEN = 300000          # exec output cap
MAX_FILE = 2000000       # put/get cap per file (raw bytes)
ACTLOG = os.path.join(WORKDIR, "activity.log")


def act(line):
    """v4.4: human-readable activity log -- boss can watch this live"""
    try:
        with open(ACTLOG, "a", encoding="utf-8", errors="replace") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), line))
    except Exception:
        pass

WORKDIR_N = os.path.normcase(os.path.abspath(WORKDIR))

SYSTEM_OPS = (
    "schtasks", "reg add", "reg delete", "reg import", "reg restore",
    "net user", "net localgroup", "net stop", "net start",
    "taskkill", "shutdown", "logoff", "diskpart", "vssadmin", "bcdedit",
    "netsh ", "sc create", "sc delete", "sc config", "setx ", "cipher /w",
    "icacls", "attrib +", "format ", "del /f /s /q c:",
    "powershell set-executionpolicy", "new-service", "remove-service",
)
ENV_OUTSIDE = ("%userprofile%", "%appdata%", "%localappdata%",
               "%programfiles%", "%programdata%", "%temp%", "%systemroot%",
               "%windir%", "%homepath%", "%allusersprofile%")

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# pythonw guard: no console -> stdout/stderr are None -> print() would crash
# v4.3: log to file instead of devnull so failures are visible remotely
try:
    os.makedirs(WORKDIR, exist_ok=True)
except Exception:
    pass
_LOG = open(os.path.join(WORKDIR, "worker.log"), "a", buffering=1, encoding="utf-8", errors="replace")
try:
    if _LOG.tell() > 200000:
        _LOG.close()
        os.replace(os.path.join(WORKDIR, "worker.log"), os.path.join(WORKDIR, "worker.log.old"))
        _LOG = open(os.path.join(WORKDIR, "worker.log"), "a", buffering=1, encoding="utf-8", errors="replace")
except Exception:
    pass
if sys.stdout is None:
    sys.stdout = _LOG
if sys.stderr is None:
    sys.stderr = _LOG


def run(cmd):
    # v4.1: unicode-safe exec + full process-tree kill on timeout (CR-4/CR-9)
    tmp = None
    full = cmd
    try:
        if os.name == "nt" and not cmd.isascii():
            # non-ascii args can hang cmd.exe arg-encoding: run via temp script
            tmp = Path(WORKDIR) / (".ab_exec_%d.cmd" % int(time.time() * 1000))
            # raw utf-8, no BOM, no chcp: cmd passes the bytes through untouched
            tmp.write_bytes(("@echo off\r\n" + cmd + "\r\n").encode("utf-8"))
            full = 'cmd /c "%s"' % tmp.name
        p = subprocess.Popen(full, shell=True, cwd=WORKDIR,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            out_b, _ = p.communicate(timeout=CMD_TIMEOUT)
            out = (out_b or b"").decode("utf-8", "replace")
            code = p.returncode
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                # kill the WHOLE tree (cmd.exe children survive p.kill alone)
                subprocess.run("taskkill /F /T /PID %d >nul 2>&1" % p.pid, shell=True)
            else:
                p.kill()
            try:
                out_b, _ = p.communicate(timeout=5)
            except Exception:
                out_b = b""
            out = (out_b or b"").decode("utf-8", "replace")
            out += "\n[TIMEOUT after %ss - process tree killed]" % CMD_TIMEOUT
            code = -1
    except Exception as e:
        out = "[worker error] %r" % e
        code = -1
    finally:
        if tmp:
            try:
                tmp.unlink()
            except Exception:
                pass
    if len(out) > MAXLEN:
        out = out[:MAXLEN // 2] + "\n...[truncated %d chars]...\n" % (len(out) - MAXLEN) + out[-MAXLEN // 2:]
    return {"output": out, "exit_code": code}


def safe_path(rel):
    # must stay inside SYNC_ROOT: no .., no drives, no absolute
    if not rel or not isinstance(rel, str):
        return None
    p = rel.replace("\\", "/").strip("/")
    parts = p.split("/")
    if ".." in parts or any(":" in s for s in parts) or not p:
        return None
    return SYNC_ROOT / Path(*parts)


# ---------------- approval policy ----------------
def load_approvals():
    try:
        a = json.loads(APPROVALS_FILE.read_text())
    except Exception:
        return {"outside_ok": False, "pending": {}}
    # v4.1: prune pending entries older than 24h (CR-3)
    pend = a.get("pending", {})
    stale = [k for k, v in pend.items()
             if not isinstance(v, dict) or time.time() - v.get("ts", 0) > 86400]
    for k in stale:
        pend.pop(k, None)
    if stale:
        a["pending"] = pend
        try:
            save_approvals(a)
        except Exception:
            pass
    return a


def save_approvals(a):
    try:
        APPROVALS_FILE.write_text(json.dumps(a, indent=2))
    except Exception:
        pass


def _inside(p):
    q = os.path.normcase(os.path.abspath(p))
    return q == WORKDIR_N or q.startswith(WORKDIR_N + os.sep)


def analyze_outside(cmd):
    """best-effort: does this command reach outside WORKDIR or do system ops?"""
    c = cmd.lower()
    # explicit absolute paths (case-insensitive: C:\ or d:/ ...)
    for m in re.finditer(r"[a-z]:[\\/][^\"'\s;,&|)<]*", cmd, re.IGNORECASE):
        if not _inside(m.group(0)):
            return "outside path: %s" % m.group(0)
    # UNC paths
    if "\\\\" in cmd:
        return "UNC/network path"
    # user/system env vars
    for v in ENV_OUTSIDE:
        if v in c:
            return "outside env var: %s" % v
    # home ~
    if re.search(r"(^|[\s&|;])~([\\/]|$)", c) or c.strip().startswith("cd ~"):
        return "home folder (~)"
    # cd / pushd outside
    for m in re.finditer(r"\b(?:cd|pushd)\s+(?:/d\s+)?([a-z]:[^\s&|;]+)", c):
        if not _inside(m.group(1)):
            return "cd outside: %s" % m.group(1)
    # system-level operations
    for kw in SYSTEM_OPS:
        if kw in c:
            return "system op: %s" % kw.strip()
    return None


def needs_approval(cmd):
    a = load_approvals()
    if a.get("outside_ok"):
        return None
    reason = analyze_outside(cmd)
    if reason is None:
        return None
    return reason


def op_put(msg):
    p = safe_path(msg.get("path"))
    if p is None:
        return {"ok": False, "error": "bad path"}
    try:
        data = base64.b64decode(msg.get("b64", ""))
        if len(data) > MAX_FILE:
            return {"ok": False, "error": "file too large (>%d bytes)" % MAX_FILE}
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        return {"ok": True, "bytes": len(data),
                "sha": hashlib.sha256(data).hexdigest()}
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def op_get(msg):
    p = safe_path(msg.get("path"))
    if p is None:
        return {"ok": False, "error": "bad path"}
    try:
        if not p.is_file():
            return {"ok": False, "error": "not found"}
        st = p.stat()
        if st.st_size > MAX_FILE:
            return {"ok": False, "error": "file too large (%d bytes)" % st.st_size}
        data = p.read_bytes()
        return {"ok": True, "size": len(data),
                "sha": hashlib.sha256(data).hexdigest(),
                "b64": base64.b64encode(data).decode()}
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def op_manifest(msg):
    files = []
    if not SYNC_ROOT.exists():
        return {"ok": True, "files": [], "root": str(SYNC_ROOT)}
    skip_dirs = {".git", "__pycache__", ".cache", "node_modules"}
    for root, dirs, fs in os.walk(SYNC_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in fs:
            fp = os.path.join(root, fn)
            try:
                st = os.stat(fp)
            except Exception:
                continue
            if st.st_size > MAX_FILE:
                continue
            try:
                h = hashlib.sha256(open(fp, "rb").read()).hexdigest()[:16]
            except Exception:
                continue
            rel = os.path.relpath(fp, SYNC_ROOT).replace("\\", "/")
            files.append({"p": rel, "s": st.st_size, "h": h})
            if len(files) >= 2000:
                return {"ok": True, "files": files, "truncated": True}
    return {"ok": True, "files": files, "root": str(SYNC_ROOT)}


def op_del(msg):
    p = safe_path(msg.get("path"))
    if p is None:
        return {"ok": False, "error": "bad path"}
    try:
        if p.is_file():
            p.unlink()
            return {"ok": True}
        return {"ok": False, "error": "not a file"}
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def op_approve(msg):
    a = load_approvals()
    pid_ = str(msg.get("approve_id", ""))
    d = msg.get("decision", "")
    ent = a.get("pending", {}).pop(pid_, None)
    if ent is None:
        return {"ok": False, "error": "no pending id %s" % pid_}
    if d == "deny":
        save_approvals(a)
        return {"ok": True, "executed": False, "denied": True,
                "cmd": ent["cmd"]}
    if d == "allow_all":
        a["outside_ok"] = True
    save_approvals(a)
    print("[approval] %s -> %s : running" % (pid_, d))
    res = run(ent["cmd"])
    print(res["output"] if res["output"].strip() else "(no output)")
    return {"ok": True, "executed": True, "decision": d,
            "output": res["output"], "exit_code": res["exit_code"]}


def op_pending():
    a = load_approvals()
    return {"ok": True, "pending": a.get("pending", {}),
            "outside_ok": bool(a.get("outside_ok"))}


def op_policy(msg):
    a = load_approvals()
    if "outside_ok" in msg:
        a["outside_ok"] = bool(msg.get("outside_ok"))
    save_approvals(a)
    return {"ok": True, "outside_ok": bool(a.get("outside_ok"))}


def secrets_hex(n):
    import secrets as _s
    return _s.token_hex(n)


def main():
    global WORKDIR
    try:
        os.makedirs(WORKDIR, exist_ok=True)
    except Exception as e:
        print("[warn] cannot create %s (%r) -- using home" % (WORKDIR, e))
        WORKDIR = os.path.expanduser("~")
    SYNC_ROOT.mkdir(parents=True, exist_ok=True)
    import platform
    info = {"system": "%s %s" % (platform.system(), platform.release()),
            "user": os.environ.get("USERNAME") or os.environ.get("USER", "?"),
            "cwd": WORKDIR, "py": sys.version.split()[0],
            "ver": "4.5.1", "sync_root": str(SYNC_ROOT)}
    print("=" * 62)
    print("  ARENABRIDGE WORKER v4 (SYNC+APPROVALS)")
    print("  machine : %(system)s   user: %(user)s   py %(py)s" % info)
    print("  cwd     : %(cwd)s" % info)
    print("  sync    : %(sync_root)s" % info)
    print("  Commands from chat run here. Ctrl+C to stop.")
    print("=" * 62)
    while True:
        for host in BROKERS:
            try:
                m = MiniMQTT(host, 1883, keepalive=30,
                             client_id="ab4-" + (os.environ.get("USERNAME") or "x")[:8].replace(" ", ""))
                m.connect(will_topic=T_PRE,
                          will_payload=mkmsg(KEY, {"online": False, "ver": "4.5.1", "ts": time.time()}),
                          will_retain=True)

                _LAST = {}   # v4.1: id+result cache -> agent retries replay, never re-execute

                def _on_cmd_inner(msg, mid, _m):
                    op = msg.get("op", "exec")
                    if op == "exec":
                        cmd = msg.get("cmd", "")
                        reason = needs_approval(cmd)
                        if reason:
                            a = load_approvals()
                            apid = secrets_hex(4)
                            a.setdefault("pending", {})[apid] = {
                                "cmd": cmd, "reason": reason, "ts": time.time()}
                            save_approvals(a)
                            act("LOCKED  %s  -- dahil: %s (hintay approval ni boss, id %s)" % (cmd, reason, apid))
                            print("\n[LOCKED] %s  --  %s" % (cmd, reason))
                            out = {"id": mid, "op": "exec",
                                   "pending_approval": True,
                                   "approve_id": apid, "reason": reason,
                                   "output": "[LOCKED] kailangan ng approval ni boss: %s\nreply: approve %s allow|allow_all|deny" % (reason, apid),
                                   "exit_code": 126}
                        else:
                            print("\n$ " + cmd)
                            t_exec = time.time()
                            res = run(cmd)
                            dur = time.time() - t_exec
                            ok = res["exit_code"] == 0
                            act("CMD     %s" % cmd)
                            act("RESULT  %s exit=%s (%.1fs)%s" % ("OK" if ok else "FAILED",
                                 res["exit_code"], dur, "" if ok else " -- output: " + res["output"].strip()[:200]))
                            print(res["output"] if res["output"].strip()
                                  else "(no output) [exit %s]" % res["exit_code"])
                            out = {"id": mid, "op": "exec",
                                   "output": res["output"], "exit_code": res["exit_code"]}
                    elif op == "note":
                        # boss-order context line, log lang (hindi command)
                        act("BOSS    %s" % msg.get("note", "")[:300])
                        out = {"id": mid, "op": "note", "ok": True}
                    elif op == "put_file":
                        r = op_put(msg)
                        print(("[file] PUT %s -> %s" % (msg.get("path"), "OK" if r.get("ok") else r.get("error"))))
                        out = dict(r, id=mid, op=op)
                    elif op == "get_file":
                        r = op_get(msg)
                        print("[file] GET %s -> %s" % (msg.get("path"), "OK" if r.get("ok") else r.get("error")))
                        out = dict(r, id=mid, op=op)
                    elif op == "manifest":
                        r = op_manifest(msg)
                        print("[file] MANIFEST -> %d files" % len(r.get("files", [])))
                        out = dict(r, id=mid, op=op)
                    elif op == "del_file":
                        r = op_del(msg)
                        print("[file] DEL %s -> %s" % (msg.get("path"), r))
                        out = dict(r, id=mid, op=op)
                    elif op == "approve":
                        r = op_approve(msg)
                        act("APPROVE id=%s decision=%s" % (msg.get("approve_id"), msg.get("decision")))
                        out = dict(r, id=mid, op=op)
                    elif op == "pending":
                        r = op_pending()
                        out = dict(r, id=mid, op=op)
                    elif op == "policy":
                        r = op_policy(msg)
                        act("POLICY  outside_ok=%s" % (r or {}).get("outside_ok"))
                        out = dict(r, id=mid, op=op)
                    else:
                        out = {"id": mid, "ok": False, "error": "unknown op %s" % op}
                    packed = mkmsg(KEY, out)
                    _LAST.update(id=mid, res=packed)
                    _m.publish(T_RES, packed)

                def on_cmd(raw, _m=m):
                    # v4.3: never-silent dispatcher -- logs + replies on any crash
                    msg = readmsg(KEY, raw)
                    if msg is None:
                        print("[blocked unsigned/bad-sig message]")
                        return
                    mid = msg.get("id")
                    if mid and mid == _LAST.get("id") and _LAST.get("res") is not None:
                        _m.publish(T_RES, _LAST["res"])   # replay cached result
                        return
                    try:
                        _on_cmd_inner(msg, mid, _m)
                    except Exception:
                        import traceback
                        tb = traceback.format_exc()[-1500:]
                        print("[on_cmd CRASH]\n" + tb)
                        try:
                            _m.publish(T_RES, mkmsg(KEY, {"id": mid, "op": "error",
                                                          "output": "[worker on_cmd crash]\n" + tb,
                                                          "exit_code": -1}))
                        except Exception:
                            pass

                m.subscribe(T_CMD, on_cmd)
                m.publish(T_PRE, mkmsg(KEY, dict(info, online=True, ts=time.time())), retain=True)
                act("WORKER  start ver 4.4 via %s" % host)
                print("[v4 connected via %s] waiting for commands..." % host)
                last_hb = time.time()
                t_conn = time.time()
                while True:
                    m.loop(1.0)
                    if time.time() - last_hb > 25:
                        hb = dict(info)
                        hb.update({"online": True, "ts": time.time()})
                        m.publish(T_PRE, mkmsg(KEY, hb), retain=True)
                        last_hb = time.time()
                    # home-bias: don't park on a fallback broker forever
                    if host != BROKERS[0] and time.time() - t_conn > 120:
                        print("[home-bias] parked on %s 120s -- returning home" % host)
                        break
            except KeyboardInterrupt:
                print("\n[v3 stopped by user]")
                sys.exit(0)
            except Exception as e:
                print("[mqtt error via %s: %r] rotating broker..." % (host, e))
                time.sleep(2)


main()
