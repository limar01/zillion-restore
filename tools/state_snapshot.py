#!/usr/bin/env python3
"""state_snapshot.py — Zillion restore-point snapshotter (v1.0)

WHY THIS EXISTS
  Every fresh Arena chat/model starts from a blank sandbox. The ONLY channel that
  reaches every model is the repo they all clone. So the restore point must live
  in the repo: MEMORY_CORE's READ MAP tells the agent to read STATE/CURRENT.md,
  which makes the snapshot load automatically on every restore, for every model.

WHAT IT DOES (read-only collection — touches nothing it reports on)
  1. resolves the live tunnel URL (trusted url.txt -> saved -> beacon)
  2. health bundle: tunnel HMAC · worker pgrep · adb devices · deploy-key ssh -T
  3. project state: every git repo in ~/Projects/workspace (+ upstream/private vault)
  4. writes STATE/CURRENT.md + STATE/state.json into a clone and optionally pushes
  5. NEVER records: HMAC key, passphrase, bootstrap hash, tokens, key material

USAGE (on the phone, in Termux)
  python3 state_snapshot.py                  # collect + write ~/zillion_pw/_urlrepo/STATE/
  python3 state_snapshot.py --push           # ... and commit+push (needs deploy key)
  python3 state_snapshot.py --json-only      # machine format only
  python3 state_snapshot.py --out DIR        # write somewhere else

EXIT CODES  0 = snapshot written · 2 = phone unreachable · 3 = push requested and failed
"""
import os, sys, json, time, subprocess, re

HOME = os.path.expanduser("~")
PW = os.path.join(HOME, "zillion_pw")
REPO = os.path.join(PW, "_urlrepo")
WORKSPACE = os.path.join(HOME, "Projects", "workspace")
STATEFILE_LAST = os.path.join(PW, "STATE", "state.json")


def sh(cmd, timeout=25):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "").strip(), (p.stderr or "").strip(), p.returncode
    except Exception as e:
        return "", repr(e), -1


def tunnel_url():
    """Trusted-first: url.txt in the clone -> saved last -> beacon (post-key ok)."""
    try:
        u = open(os.path.join(REPO, "url.txt")).read().strip()
        if u and ping(u):
            return u, "url.txt(trusted)"
    except Exception:
        pass
    try:
        u = open(os.path.join(HOME, "zillion_phone_cf_url.txt")).read().strip()
        if u and ping(u):
            return u, "saved"
    except Exception:
        pass
    try:
        out, _, _ = sh("timeout 12 python3 -c \"import sys;sys.path.insert(0,'%s');"
                       "from bridge import phone_tun as p;print(p.discover_mqtt(8).get('url',''))\"" % HOME, 20)
        u = out.splitlines()[-1].strip() if out else ""
        if u and ping(u):
            return u, "beacon"
    except Exception:
        pass
    return "", "none"


def ping(u):
    try:
        import urllib.request
        with urllib.request.urlopen((u or "").rstrip("/") + "/ping", timeout=6) as r:
            return r.status == 200
    except Exception:
        return False


def health():
    h = {}
    w, _, _ = sh("pgrep -a -f '/arenabridge/worker.py' | grep -v pgrep | head -1")
    h["worker"] = w.split(" ", 1)[0] if w else ""
    h["worker_alive"] = bool(w)
    a, _, _ = sh("adb devices 2>/dev/null | awk 'NR>1 && NF'")
    devs = [l.split("\t")[0] for l in a.splitlines() if "device" in l]
    h["adb_devices"] = devs
    h["adb_alive"] = any("device" in l for l in a.splitlines())
    for alias in ("github-zr", "github-ta", "github-shopee"):
        o, e, rc = sh("timeout 12 ssh -o ConnectTimeout=8 -T %s 2>&1 | head -1" % alias, 18)
        line = (o or e).strip()
        h["key_" + alias.replace("github-", "")] = ("OK: " + line) if "successfully authenticated" in line else "REJECTED"
    h["model"] = sh("getprop ro.product.model")[0]
    h["android"] = sh("getprop ro.build.version.release")[0]
    h["uptime"] = sh("uptime -p 2>/dev/null || uptime")[0]
    return h


def projects():
    out = []
    if not os.path.isdir(WORKSPACE):
        return out
    for name in sorted(os.listdir(WORKSPACE)):
        d = os.path.join(WORKSPACE, name)
        if not os.path.isdir(d):
            continue
        p = {"name": name, "git": os.path.isdir(os.path.join(d, ".git"))}
        if p["git"]:
            p["branch"] = sh("git -C '%s' rev-parse --abbrev-ref HEAD" % d)[0] or "?"
            p["last_commit"] = sh("git -C '%s' log -1 --format='%%h %%ad %%s' --date=short" % d)[0]
            dirty = sh("git -C '%s' status --porcelain" % d)[0]
            p["dirty_files"] = len(dirty.splitlines()) if dirty else 0
            p["ahead"] = sh("git -C '%s' rev-list --count @{u}..HEAD 2>/dev/null" % d)[0] or "0"
        newest, newest_ts = "", 0.0
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x not in (".git", "node_modules", ".venv", "__pycache__")]
            for f in files:
                try:
                    ts = os.path.getmtime(os.path.join(root, f))
                    if ts > newest_ts:
                        newest_ts, newest = ts, os.path.relpath(os.path.join(root, f), d)
                except Exception:
                    pass
        p["newest_file"] = newest
        p["newest_at"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(newest_ts)) if newest_ts else ""
        out.append(p)
    return out


def last_task(projs):
    """Honest last-task: explicit handoff if it exists, else newest project activity."""
    for cand in ("CURRENT_HANDOFF.md", "HANDOFF.md", "zillion_pw/CURRENT_HANDOFF"):
        for base in (HOME, PW, WORKSPACE):
            f = os.path.join(base, cand)
            if os.path.isfile(f):
                raw = open(f, errors="ignore").read()
                task = ""
                # preferred: an explicit "## LAST_TASK" section, first paragraph
                m = re.search(r"^#{1,6}\s*LAST_TASK[^\n]*\n+(.+?)(?=\n\s*\n|\n#{1,6}\s|\Z)", raw, re.S | re.M)
                if m:
                    task = " ".join(m.group(1).split())
                if not task:  # fallback: first non-heading line
                    for l in raw.splitlines():
                        if l.strip() and not l.lstrip().startswith("#"):
                            task = l.strip(); break
                if task:
                    if len(task) > 220:
                        task = task[:217].rsplit(" ", 1)[0] + "…"
                    return {"last_task": task, "source": f, "explicit": True}
    if not projs:
        return {"last_task": "no project activity found", "source": None, "explicit": False}
    p = max(projs, key=lambda x: x.get("newest_at") or "")
    return {"last_task": "%s — newest file %s (%s)" % (p["name"], p["newest_file"], p["newest_at"]),
            "source": "newest-mtime", "explicit": False}


def scrub(snap):
    """B-mode redaction for the PUBLIC repo. Keeps what an agent needs to resume
    (project name, branch, dirty counts, LAST_TASK) and removes what it does not:
    LAN addresses and commit subjects. --full disables this for the private vault."""
    import copy
    s = copy.deepcopy(snap)
    s["redacted"] = True
    # device transports: keep loopback (not sensitive), mask anything routable
    s["health"]["adb_devices"] = [
        d if d.startswith("127.0.0.1") else "<lan-transport:redacted>"
        for d in s["health"].get("adb_devices", [])
    ]
    s["health"]["adb_count"] = len(snap["health"].get("adb_devices", []))
    for k in ("key_zr", "key_ta", "key_shopee"):
        v = s["health"].get(k) or ""
        s["health"][k] = "OK" if "successfully authenticated" in v else "REJECTED"
    # project commit subjects are work content -> hash + date only
    for p in s["projects"]:
        lc = p.get("last_commit") or ""
        toks = lc.split(" ")
        p["last_commit"] = " ".join(toks[:2]) if len(toks) >= 2 else lc
    return s


def render(snap):
    h, projs, lt = snap["health"], snap["projects"], snap["last_task"]
    ok = lambda b: "LIVE" if b else "DOWN"
    L = []
    L.append("# Zillion restore point — STATE/CURRENT")
    L.append("")
    L.append("> **Auto-generated. Do not hand-edit.** Regenerate with `python3 ~/zillion_pw/state_snapshot.py --push`.")
    L.append("> Read this FIRST on restore (see READ MAP), then continue the last task. Snapshot is scrubbed: no keys, no passphrase.")
    if snap.get("redacted"):
        L.append("> **Redacted for the public repo:** LAN addresses and commit subjects removed.")
    L.append("")
    L.append("**Snapshot:** %s · **lane:** phone · **host:** %s / Android %s · **uptime:** %s"
             % (snap["taken_at"], h["model"], h["android"], h["uptime"]))
    L.append("")
    L.append("## Component state")
    L.append("| Component | State |")
    L.append("|---|---|")
    L.append("| Tunnel | %s — `%s` (via %s) |" % (ok(bool(snap["tunnel"])), snap["tunnel"] or "-", snap["tunnel_source"]))
    L.append("| Bridge Worker | %s (pid %s) |" % (ok(h["worker_alive"]), h["worker"] or "-"))
    L.append("| adb | %s — %s (%s transport(s)) |" % (ok(h["adb_alive"]), ", ".join(h["adb_devices"]) or "no devices", h.get("adb_count", len(h["adb_devices"]))))
    L.append("| Deploy keys | zr=%s · ta=%s · shopee=%s |" % (h.get("key_zr"), h.get("key_ta"), h.get("key_shopee")))
    L.append("")
    L.append("## LAST_TASK (what the next agent resumes)")
    L.append("**%s**" % lt["last_task"])
    L.append("")
    L.append("_source: %s%s_" % (lt["source"], "" if lt["explicit"] else " — **inferred from file mtimes, not a declared handoff**"))
    L.append("")
    L.append("## Projects")
    if projs:
        for p in projs:
            L.append("- **%s** · branch `%s` · last `%s` · dirty %d · ahead %s"
                     % (p["name"], p.get("branch", "-"), p.get("last_commit", "-"), p.get("dirty_files", 0), p.get("ahead", "0")))
            L.append("  - newest: `%s` (%s)" % (p.get("newest_file", "-"), p.get("newest_at", "-")))
    else:
        L.append("- _(none found under `~/Projects/workspace/`)_")
    L.append("")
    L.append("## Restore hint")
    L.append("1. clone repo → read `MEMORY_CORE.md` per READ MAP → **read this file**")
    L.append("2. bootstrap key, verify HMAC `/ping` against the tunnel above (it rotates — trust `url.txt` first)")
    L.append("3. verify worker + adb independently; only claim LIVE what you verified")
    L.append("4. resume: %s" % lt["last_task"])
    L.append("")
    return "\n".join(L)


def fingerprint(snap):
    """Stable hash of state that matters — excludes timestamps so an unchanged
    system produces no commit. Lets a 5-min cron run safely."""
    import hashlib
    core = {
        "tunnel": snap["tunnel"],
        "worker": snap["health"]["worker_alive"],
        "adb": snap["health"]["adb_devices"],
        "keys": [snap["health"].get("key_zr"), snap["health"].get("key_ta"), snap["health"].get("key_shopee")],
        "projects": [{k: v for k, v in p.items() if k not in ("newest_at",)} for p in snap["projects"]],
        "last_task": snap["last_task"]["last_task"],
    }
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]


def previous_fingerprint():
    try:
        return fingerprint(json.load(open(STATEFILE_LAST)))
    except Exception:
        return ""


def main():
    args = sys.argv[1:]
    push = "--push" in args
    if_changed = "--if-changed" in args
    redact = "--full" not in args   # public repo default = redacted
    json_only = "--json-only" in args
    outdir = REPO
    if "--out" in args:
        outdir = args[args.index("--out") + 1]

    url, src = tunnel_url()
    snap = {
        "schema": "zillion.state/1",
        "taken_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "taken_ts": time.time(),
        "lane": "phone",
        "tunnel": url,
        "tunnel_source": src,
        "health": health(),
        "projects": projects(),
    }
    snap["last_task"] = last_task(snap["projects"])
    snap["fingerprint"] = fingerprint(snap)
    if redact:
        snap = scrub(snap)

    if if_changed and snap["fingerprint"] == previous_fingerprint():
        print("no state change (fingerprint %s) — snapshot skipped" % snap["fingerprint"])
        return 0

    os.makedirs(os.path.join(outdir, "STATE"), exist_ok=True)
    jpath = os.path.join(outdir, "STATE", "state.json")
    mpath = os.path.join(outdir, "STATE", "CURRENT.md")
    with open(jpath, "w") as f:
        json.dump(snap, f, indent=1)
    md = render(snap)
    with open(mpath, "w") as f:
        f.write(md)
    os.makedirs(os.path.dirname(STATEFILE_LAST), exist_ok=True)
    try:
        open(STATEFILE_LAST, "w").write(json.dumps(snap, indent=1))
    except Exception:
        pass

    if json_only:
        print(json.dumps(snap, indent=1))
    else:
        print("snapshot written: %s (+ state.json)" % mpath)
        print("  tunnel : %s (%s)" % (url or "NONE", src))
        print("  worker : %s | adb: %s" % ("LIVE" if snap["health"]["worker_alive"] else "DOWN",
                                            "LIVE" if snap["health"]["adb_alive"] else "DOWN"))
        print("  last   : %s" % snap["last_task"]["last_task"])
        print("  fp     : %s" % snap["fingerprint"])

    if push:
        sh("git -C '%s' add STATE" % outdir)
        o, e, rc = sh("git -C '%s' commit -qm 'state: restore point %s'" % (outdir, snap["taken_at"]), 30)
        if rc != 0 and "nothing to commit" in (o + e):
            print("push: nothing to commit (state unchanged)")
            return 0
        o, e, rc = sh("git -C '%s' push -q origin main" % outdir, 60)
        if rc != 0:
            print("push FAILED:", (e or o).splitlines()[-1] if (e or o) else "unknown")
            print("  -> deploy key github-zr likely not registered. State is still written locally.")
            return 3
        print("push: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
