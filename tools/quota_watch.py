#!/usr/bin/env python3
"""quota_watch.py -- arena.ai daily/rate-limit watcher (zillionOM PC lane, v1.0)

WHY: the red-triangle "You've reached your daily usage limit" state kills the chat
BEFORE Boss can type `wrap`. This daemon catches the limit the moment it happens,
auto-saves the phone restore point (the mechanical half of `wrap`), and notifies.

SIGNALS
  A) API poll  : GET https://arena.ai/api/me (optional Cookie: ~/.arena_cookie)
                 - IETF `ratelimit:` headers  -> burst early-warning (limit/remaining/reset)
                 - 429 body/headers          -> hard limit (daily vs burst, + reset time)
                 - 401/403 with cookie file  -> auth stale (notify once)
  B) UI watch  : opt-in --ui-monitor NAME -> grim+magick red-triangle detection on the
                 bottom-right of that Hyprland monitor (post-limit, certain, zero-auth).
                 Passive observation only -- never drives the browser (rule 10).

ACTIONS (only on state CHANGE; hysteresis + 15-min re-checkpoint floor)
  - notify-send (critical on limit)
  - JSONL log    : ~/arenabridge/quota_watch.log
  - state file   : ~/arenabridge/quota_watch.state  (agent-readable via CF tunnel)
  - auto-checkpoint (default ON at LIMIT, opt-in at WARN): runs the phone-side
    checkpoint.py over the phone CF tunnel (shared HMAC key; phone URL from the
    signed ph/pres beacon). This is what `wrap` does mechanically.

USAGE
  python3 quota_watch.py [--interval 90] [--warn-remaining 300]
                         [--ui-monitor DVI-D-1] [--checkpoint-on-warn] [--no-checkpoint]
  python3 quota_watch.py --once     # single poll, prints state JSON (for status reads)
"""
import argparse, hashlib, hmac, json, os, subprocess, sys, time, urllib.error, urllib.request, uuid

HOME = os.path.expanduser("~")
AB = os.path.join(HOME, "arenabridge")
KEY_PATH = os.path.join(AB, "arenabridge.key")
LOG = os.path.join(AB, "quota_watch.log")
STATE = os.path.join(AB, "quota_watch.state")
ME_SAMPLE = os.path.join(AB, "quota_watch.me_sample.json")
COOKIE = os.path.join(HOME, ".arena_cookie")
SID = "53cf4a5803c91726b892e5d0785085c6"
API = "https://arena.ai/api/me"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:155.0) Gecko/20100101 Firefox/155.0"
RE_CP_FLOOR = 900  # seconds between auto-checkpoints


def iso(ts=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts or time.time()))


def log(obj):
    obj = dict(obj)
    obj.setdefault("ts", time.time())
    obj.setdefault("iso", iso(obj["ts"]))
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps(obj) + "\n")
    except Exception:
        pass


def notify(title, body, urgency="normal"):
    try:
        subprocess.run(["notify-send", "-u", urgency, "-a", "zillion-quota-watch", title, body],
                       timeout=10, capture_output=True)
        return True
    except Exception as e:
        log({"event": "notify_fail", "err": repr(e)})
        return False


def read_cookie():
    try:
        c = open(COOKIE).read().strip()
        return c or None
    except Exception:
        return None


def poll_api():
    hdr = {"User-Agent": UA, "Accept": "*/*"}
    c = read_cookie()
    if c:
        hdr["Cookie"] = c
    req = urllib.request.Request(API, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers), e.read()
        except Exception:
            return e.code, dict(e.headers), b""
    except Exception as e:
        return -1, {}, repr(e).encode()


def parse_rl(hdrs):
    out = {}
    raw = hdrs.get("ratelimit") or hdrs.get("RateLimit") or ""
    for part in raw.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                out[k.strip()] = float(v.strip())
            except ValueError:
                pass
    return out


def ui_probe(monitor, crop):
    """Fraction of reddish pixels in the bottom-right crop of a monitor."""
    try:
        png = os.path.join(AB, "quota_ui.png")
        r = subprocess.run(["grim", "-o", monitor, png], capture_output=True, timeout=25)
        if r.returncode != 0:
            return None
        r2 = subprocess.run(
            ["magick", png, "-gravity", "SouthEast", "-crop", crop + "+0+0", "+repage",
             "-fx", "r>0.45&&r>1.5*g&&r>1.5*b?1:0", "-format", "%[fx:mean]", "info:"],
            capture_output=True, timeout=25)
        if r2.returncode != 0:
            return None
        return float(r2.stdout.decode().strip() or 0)
    except Exception as e:
        log({"event": "ui_probe_fail", "err": repr(e)})
        return None


def phone_url(timeout=10):
    """Fresh phone tunnel URL from the signed ph/pres beacon (MQTT, broker rotation)."""
    try:
        import paho.mqtt.client as mqtt
    except Exception:
        return "", {}
    try:
        key = open(KEY_PATH).read().strip()
    except Exception:
        return "", {}
    found = {}

    def on_msg(c, u, msg):
        try:
            env = json.loads(msg.payload.decode())
            d, h = env.get("d", ""), env.get("h", "")
            if h:
                exp = hmac.new(key.encode(), d.encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(h, exp):
                    return
            found.update(json.loads(d))
        except Exception:
            pass

    for host in ["broker.emqx.io", "broker.hivemq.com", "test.mosquitto.org"]:
        try:
            cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="qw_" + uuid.uuid4().hex[:6])
            cl.on_message = on_msg
            cl.connect(host, 1883, keepalive=20)
            cl.subscribe(f"arenabridge/{SID}/ph/pres", qos=1)
            cl.loop_start()
            t0 = time.time()
            while time.time() - t0 < timeout / 3 and not (
                    found.get("url") and time.time() - found.get("ts", 0) < 180):
                time.sleep(0.1)
            cl.loop_stop()
            cl.disconnect()
        except Exception:
            continue
        if found.get("url"):
            return found["url"].rstrip("/"), found
    return "", found


def phone_checkpoint(summary, handoff):
    """Run the phone-side checkpoint.py over the phone CF tunnel (HMAC exec)."""
    url, _ = phone_url()
    if not url:
        return False, "no fresh phone tunnel URL"
    try:
        key = open(KEY_PATH).read().strip()
    except Exception as e:
        return False, "no key: %r" % e
    body = json.dumps({"event_id": "auto-wrap-" + uuid.uuid4().hex[:8],
                       "summary": summary, "handoff": handoff})
    cmd = ("cd ~/Projects/workspace/zillion-doctrine/tunnel-adb 2>/dev/null && "
           "python3 memory/tools/checkpoint.py <<'QWEOF'\n" + body + "\nQWEOF")
    payload = {"op": "exec", "id": "qw_" + uuid.uuid4().hex[:6], "cmd": cmd,
               "timeout": 75, "ts": time.time()}
    d = json.dumps(payload, separators=(",", ":"))
    env = json.dumps({"d": d, "h": hmac.new(key.encode(), d.encode(), hashlib.sha256).hexdigest()}).encode()
    req = urllib.request.Request(url + "/", data=env,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            out = json.loads(json.loads(r.read().decode())["d"])
        return out.get("exit_code") == 0, (out.get("output") or out.get("error") or "")[-400:]
    except Exception as e:
        return False, repr(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=90)
    ap.add_argument("--warn-remaining", type=float, default=300)
    ap.add_argument("--ui-monitor", default=None, help="Hyprland monitor name for red-triangle watch")
    ap.add_argument("--ui-crop", default="460x150")
    ap.add_argument("--ui-threshold", type=float, default=0.01)
    ap.add_argument("--checkpoint-on-warn", action="store_true")
    ap.add_argument("--no-checkpoint", action="store_true")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    prev, n, ui_streak, last_cp = -1, 0, 0, 0.0
    while True:
        n += 1
        status, hdrs, body = poll_api()
        rl = parse_rl(hdrs)
        level, why = 0, "ok"

        if status == 429:
            level = 2
            txt = body.decode("utf-8", "replace")[:300]
            why = "429 DAILY limit" if "daily" in txt.lower() else "429 rate limit"
            rst = hdrs.get("RateLimit-Reset") or hdrs.get("RateLimit-Reset".lower()) or hdrs.get("retry-after")
            if rst:
                why += " reset=%s" % rst
        elif status in (401, 403):
            why = "auth %d %s" % (status, "(cookie stale - refresh ~/.arena_cookie)" if read_cookie() else "(no cookie file)")
        elif status < 0:
            why = "poll error: %s" % body.decode("utf-8", "replace")[:120]
        else:
            rem, lim, rst = rl.get("remaining"), rl.get("limit"), rl.get("reset")
            if rem is not None and rem <= args.warn_remaining and (rst is None or rst >= 30):
                level = 1
                why = "burst remaining %.0f/%.0f reset=%.0fs" % (rem, lim or 0, rst or 0)

        if args.ui_monitor:
            frac = ui_probe(args.ui_monitor, args.ui_crop)
            if frac is not None and frac >= args.ui_threshold:
                ui_streak += 1
                if ui_streak >= 2:
                    level = 2
                    why = "UI red-triangle (%.3f, streak %d)" % (frac, ui_streak)
            else:
                ui_streak = 0

        st = {"level": level, "why": why, "http": status, "ratelimit": rl,
              "ui_monitor": args.ui_monitor, "ts": time.time(), "iso": iso()}
        try:
            with open(STATE, "w") as f:
                json.dump(st, f)
        except Exception:
            pass

        if status == 200 and not os.path.exists(ME_SAMPLE):
            try:
                with open(ME_SAMPLE, "wb") as f:
                    f.write(body)
                os.chmod(ME_SAMPLE, 0o600)
                log({"event": "me_sample_saved", "bytes": len(body)})
            except Exception:
                pass

        if level != prev:
            log({"event": "state", "from": prev, "to": level, "why": why, "ratelimit": rl})
            if level == 2:
                notify("Arena usage LIMIT reached",
                       why + " -- auto-checkpoint running. Open a NEW chat after.", "critical")
                if not args.no_checkpoint and time.time() - last_cp >= RE_CP_FLOOR:
                    last_cp = time.time()
                    ok, out = phone_checkpoint(
                        "AUTO-WRAP: arena.ai usage limit hit; restore point saved by quota_watch daemon",
                        "Auto checkpoint by quota_watch (zillionOM PC lane). Boss: open a NEW chat and "
                        "restore with the zillionOM line. No secrets in this entry.")
                    log({"event": "auto_checkpoint", "ok": ok, "out": out})
                    notify("Auto-checkpoint " + ("OK" if ok else "FAILED"),
                           ("Restore point saved." if ok else out[:200]),
                           "normal" if ok else "critical")
            elif level == 1:
                notify("Arena rate-limit warning", why + " -- consider `wrap` soon", "normal")
                if args.checkpoint_on_warn and not args.no_checkpoint and time.time() - last_cp >= RE_CP_FLOOR:
                    last_cp = time.time()
                    ok, out = phone_checkpoint(
                        "AUTO-WRAP (warn tier): arena.ai burst quota low; pre-emptive restore point",
                        "Pre-emptive checkpoint by quota_watch (zillionOM PC lane). No secrets.")
                    log({"event": "auto_checkpoint_warn", "ok": ok, "out": out})
            elif level < prev:
                notify("Arena quota recovered", why, "low")
            prev = level

        if n % 20 == 0:
            log({"event": "heartbeat", "level": level, "why": why, "ratelimit": rl})
        if args.once:
            print(json.dumps(st))
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
