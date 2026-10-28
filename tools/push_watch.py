#!/usr/bin/env python3
"""push_watch.py — Zillion publish/health watchdog (v1.0, phone lane)

WHY: the 2026-10-14 → 10-28 outage was not a crash, it was SILENCE. The beacon logged
33,031 identical, undated failures and nobody noticed. This watchdog watches the thing
that actually broke: the trusted channel reaching GitHub — plus the three components a
restore claims are live.

DESIGN RULES (kept deliberately conservative)
  - NEVER restarts worker/supervisor/tunnel. Alerting only. (KILL-LOOP rule: an auto-restart
    loop on a crashing process is worse than a down process.)
  - Self-heal ONLY the safe, local, idempotent action: re-running the snapshot push.
  - Alerts on STATE CHANGE, not on every cycle, with a per-condition cooldown (default 30 min).
  - EVERY log line is timestamped — the absence of timestamps is what hid the last outage.
  - No secrets written anywhere. No network calls except raw.githubusercontent.com + /ping.

CHECKS (one cycle)
  1. TRUSTED  url.txt on GitHub == live tunnel URL        (the original failure)
  2. TUNNEL   GET <trusted>/ping -> 200
  3. WORKER   anchored pgrep of arenabridge/worker.py
  4. ADB      adb devices contains a 'device' entry
  5. REPO     urlrepo clean, ahead==0, remote ref fresh (< STALE_PUSH_S)

ALERT CHANNELS (all best-effort, no dependency on any single one)
  - termux-notification / termux-toast (phone-visible)
  - ~/zillion_pw/watch.log (timestamped, rotated at 1 MB)
  - STATE/ALERT.md committed+pushed to the repo (survives a dead phone session)

USAGE
  python3 push_watch.py                 # one cycle, print verdict
  python3 push_watch.py --loop 120      # continuous, 2-min cycles
  python3 push_watch.py --simulate stale  # fire the alert path without breaking anything
  python3 push_watch.py --quiet         # log only, still notifies

EXIT  0 healthy/alerts-sent · 1 degraded · 2 unrecoverable (repo/push broken)
"""
import os, sys, json, time, hashlib, subprocess, urllib.request, re

HOME = os.path.expanduser("~")
PW = os.path.join(HOME, "zillion_pw")
REPO = os.path.join(PW, "_urlrepo")
LOG = os.path.join(PW, "watch.log")
STATE = os.path.join(PW, "watch_state.json")
ALERT_MD = os.path.join(REPO, "STATE", "ALERT.md")
PIDFILE = os.path.join(PW, "watch.pid")
RAW_URL = "https://raw.githubusercontent.com/limar01/zillion-restore/main/url.txt"
STALE_PUSH_S = 3600      # remote ref older than this = publishing is dead
COOLDOWN_S = 1800
MAX_LOG = 1024 * 1024


def ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = "[%s] %s" % (ts(), msg)
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > MAX_LOG:
            os.replace(LOG, LOG + ".1")
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    return line


def sh(cmd, timeout=25):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "").strip(), (p.stderr or "").strip(), p.returncode
    except Exception as e:
        return "", repr(e), -1


def notify(title, body, critical=True):
    sent = []
    prio = "max" if critical else "default"
    o, e, rc = sh('termux-notification --title "%s" --content "%s" --priority %s --id zillionwatch 2>&1'
                  % (title.replace('"', "'"), body.replace('"', "'")[:200], prio), 20)
    sent.append("termux-notification" if rc == 0 else "notif-fail")
    if critical:
        sh('termux-toast -g middle "%s" 2>&1' % title.replace('"', "'")[:60], 15)
    return ",".join(sent)


def get(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode(errors="ignore")
    except Exception as e:
        return 0, repr(e)


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def save_state(s):
    try:
        json.dump(s, open(STATE, "w"))
    except Exception:
        pass


# ---------------------------------------------------------------- checks
def check_trusted():
    """THE ORIGINAL BUG: url.txt pointing somewhere dead while the phone is fine."""
    local = ""
    try:
        local = open(os.path.join(REPO, "url.txt")).read().strip()
    except Exception:
        pass
    code, remote = get(RAW_URL, 12)
    remote = (remote or "").strip()
    if code != 200:
        return "down", "cannot read url.txt from GitHub (http=%s)" % code
    if not remote.startswith("https://"):
        return "down", "url.txt content invalid: %r" % remote[:60]
    c2, _ = get(remote.rstrip("/") + "/ping", 8)
    if c2 != 200:
        return "down", "url.txt advertises DEAD url %s (ping=%s)" % (remote, c2)
    if local and local.rstrip("/") != remote.rstrip("/"):
        return "warn", "url.txt lags local (%s vs %s) - beacon push behind" % (remote, local)
    return "ok", "url.txt -> %s (live)" % remote


def check_worker():
    o, _, _ = sh("pgrep -a -f '/arenabridge/worker.py' | grep -v pgrep | head -1")
    return ("ok", "pid %s" % o.split(" ", 1)[0]) if o else ("down", "worker.py not running")


def check_adb():
    o, _, _ = sh("adb devices 2>/dev/null | awk 'NR>1 && NF'")
    devs = [l for l in o.splitlines() if re.search(r"\tdevice\b", l)]
    return ("ok", "%d transport(s)" % len(devs)) if devs else ("down", "no adb device")


DIRTY_IGNORE = ("STATE/",)   # written by this watchdog + state_snapshot; never a fault


def check_repo():
    o, _, rc = sh("git -C '%s' status --porcelain" % REPO)
    if rc != 0:
        return "down", "urlrepo unreadable (corrupt .git?)"
    lines = [l for l in o.splitlines() if l.strip()]
    dirty = len([l for l in lines if l[3:].strip().strip('"') not in ("",) and not l[3:].strip().startswith(DIRTY_IGNORE)])
    ahead, _, _ = sh("git -C '%s' rev-list --count origin/main..HEAD 2>/dev/null" % REPO)
    ref = os.path.join(REPO, ".git", "refs", "remotes", "origin", "main")
    try:
        age = time.time() - os.path.getmtime(ref)
    except Exception:
        age = 0
    if dirty:
        return "warn", "%d uncommitted file(s) in urlrepo" % dirty
    if (ahead or "0").strip() not in ("0", ""):
        return "warn", "%s commit(s) unpushed" % ahead
    if age > STALE_PUSH_S:
        return "down", "no successful push in %d min (remote ref stale)" % (age // 60)
    return "ok", "clean, pushed %d min ago" % (age // 60)


CHECKS = [("TRUSTED", check_trusted), ("TUNNEL", None), ("WORKER", check_worker),
          ("ADB", check_adb), ("REPO", check_repo)]


def run_cycle(verbose=True, quiet=False):
    results = {}
    for name, fn in CHECKS:
        if fn is None:
            continue
        try:
            status, detail = fn()
        except Exception as e:
            status, detail = "down", "check raised %r" % (e,)
        results[name] = {"status": status, "detail": detail}

    st0 = load_state()
    # transient dirtiness is normal during legitimate work (a copy, a pull, a commit in flight).
    # Only call it a fault when it survives one full cycle.
    rp = results.get("REPO", {})
    if rp.get("status") == "warn" and "uncommitted" in rp.get("detail", ""):
        streak = int(st0.get("dirty_streak", 0)) + 1
        if streak < 2:
            results["REPO"] = {"status": "ok", "detail": rp["detail"] + " (transient, streak %d)" % streak}
        st0["dirty_streak"] = streak
    else:
        st0["dirty_streak"] = 0

    bad = {k: v for k, v in results.items() if v["status"] != "ok"}
    verdict = "DEGRADED" if bad else "HEALTHY"
    if verbose:
        for k, v in results.items():
            print("  %-8s %-4s %s" % (k, v["status"].upper(), v["detail"]))
        print("  =>", verdict)

    signature = hashlib.sha256(
        json.dumps({k: v["status"] for k, v in results.items()}, sort_keys=True).encode()
    ).hexdigest()[:12]

    st = load_state()
    prev = st.get("signature")
    last_alert = st.get("last_alert_ts", 0)

    if bad:
        log("DEGRADED %s :: %s" % (signature, "; ".join("%s=%s(%s)" % (k, v["status"], v["detail"]) for k, v in bad.items())))
        # safe self-heal: only the local idempotent push
        healed = []
        rep = results.get("REPO", {})
        if results.get("TRUSTED", {}).get("status") == "down" or rep.get("status") == "down":
            o, e, rc = sh("cd '%s' && python3 '%s' --push 2>&1 | tail -2" % (PW, os.path.join(PW, "state_snapshot.py")), 150)
            healed.append("snapshot-push rc=%s" % rc)
            log("self-heal: " + " | ".join(healed) + " :: " + (o or e)[-160:].replace("\n", " "))
        if not quiet and (signature != prev or time.time() - last_alert > COOLDOWN_S):
            title = "ZILLION: %s" % (" / ".join(sorted(bad.keys())))
            body = " | ".join("%s: %s" % (k, v["detail"]) for k, v in bad.items())
            ch = notify("⚠ " + title, body)
            log("ALERT sent via %s :: %s" % (ch, body))
            try:
                os.makedirs(os.path.dirname(ALERT_MD), exist_ok=True)
                with open(ALERT_MD, "w") as f:
                    f.write("# ⚠ ALERT — %s\n\n" % ts())
                    f.write("| Check | State | Detail |\n|---|---|---|\n")
                    for k, v in results.items():
                        f.write("| %s | %s | %s |\n" % (k, v["status"].upper(), v["detail"]))
                    f.write("\n_Auto-written by push_watch.py. Cleared on recovery._\n")
                sh("git -C '%s' add STATE/ALERT.md && git -C '%s' commit -qm 'alert: %s' && git -C '%s' push -q origin main"
                   % (REPO, REPO, ",".join(sorted(bad)), REPO), 90)
            except Exception as e:
                log("alert publish failed: %r" % (e,))
        st0.update({"signature": signature, "last_alert_ts": time.time(), "status": verdict})
        save_state(st0)
        return 1

    if prev and prev != signature:
        log("RECOVERED %s (was %s)" % (signature, prev))
        if not quiet:
            notify("✅ ZILLION recovered", "all checks OK", critical=False)
        if os.path.exists(ALERT_MD):
            try:
                os.remove(ALERT_MD)
                sh("git -C '%s' add -A STATE && git -C '%s' commit -qm 'alert cleared: recovered' && git -C '%s' push -q origin main" % (REPO, REPO, REPO), 90)
            except Exception:
                pass
    elif signature != prev:
        log("HEALTHY %s :: %s" % (signature, "; ".join("%s=%s" % (k, v["detail"]) for k, v in results.items())))
    st0.update({"signature": signature, "last_alert_ts": last_alert, "status": verdict})
    save_state(st0)
    return 0


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def running_pid():
    """Single-instance truth. Greps on process tables lie here: any 'sh -c' wrapper
    containing the script name matches itself (the anchored-pgrep trap)."""
    try:
        pid = open(PIDFILE).read().strip()
        if pid and pid_alive(pid):
            return int(pid)
    except Exception:
        pass
    return 0


def main():
    args = sys.argv[1:]

    if "--status" in args:
        pid = running_pid()
        print("watchdog: RUNNING pid %d" % pid if pid else "watchdog: NOT running")
        try:
            print("last log lines:")
            print("\n".join(open(LOG).read().strip().splitlines()[-5:]))
        except Exception:
            print("  (no log yet)")
        return 0 if pid else 1

    quiet = "--quiet" in args
    if "--simulate" in args:
        what = args[args.index("--simulate") + 1] if len(args) > args.index("--simulate") + 1 else "stale"
        log("SIMULATE %s" % what)
        ch = notify("⚠ ZILLION: SIMULATED %s" % what.upper(),
                    "Test alert from push_watch.py - no real fault. TRUSTED: simulated stale url.txt")
        print(log("ALERT(test) via %s" % ch))
        return 0
    if "--loop" in args:
        n = int(args[args.index("--loop") + 1]) if len(args) > args.index("--loop") + 1 else 120
        pid = running_pid()
        if pid:
            print("already running (pid %d) - not starting a second instance" % pid)
            return 0
        open(PIDFILE, "w").write(str(os.getpid()))
        import atexit
        atexit.register(lambda: os.path.exists(PIDFILE) and os.remove(PIDFILE))
        log("watchdog start pid=%d loop=%ss" % (os.getpid(), n))
        while True:
            try:
                rc = run_cycle(verbose=False, quiet=quiet)
                log("cycle rc=%s" % rc)
            except Exception as e:
                log("cycle EXCEPTION %r" % (e,))
            time.sleep(n)
    print("[%s] push_watch" % ts())
    return run_cycle(verbose=True, quiet=quiet)


if __name__ == "__main__":
    sys.exit(main())
