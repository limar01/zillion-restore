#!/usr/bin/env python3
"""quota_guard.py — Zillion quota & context guardrail (v2.3.2)
========================================================================
HONEST SCOPE (doctrine Rule 2 — no pretending):
The platform's real daily-quota counter and the exact context-window size
are SERVER-SIDE. They are NOT visible to any agent, and there is no meter
to query. This tool therefore MANAGES usage — it never circumvents limits.

What it does:
  1. est      — estimate tokens from text/chars (chars/4 heuristic, --ratio)
  2. budget   — keep a LOCAL daily record of ESTIMATED spend as a pacing
                reference (state file; NOT the platform counter)
  3. context  — apply doctrine Rule 9 thresholds (50/65/80/90) to the
                current estimated context usage -> concrete action
  4. preflight— estimate any text BEFORE it gets pasted into chat

Key mechanic (why this matters): every chat turn re-sends the WHOLE
conversation. Big dumps + marathon sessions without a savepoint burn the
quota fastest. Savepoint-and-new-chat at ~80% cuts context pressure AND
per-turn cost at the same time.

Defaults are PACING REFERENCES ONLY — set --daily to the real plan limit
when Boss knows it, and --window to the real context size when known.
Stdlib only, public-safe, no secrets, no network.
"""
import json, os, sys, time, argparse

CHARS_PER_TOKEN = 4.0          # heuristic: EN/TL prose ~4 chars/token; code denser (~3). Use --ratio.
DEFAULT_WINDOW  = 128_000      # reference context window (override with --window)
DEFAULT_DAILY   = 1_000_000    # PACING REFERENCE ONLY — not a known platform limit
STATE = os.path.expanduser(os.environ.get("QG_STATE", "~/.zillion_quota.json"))

# band semantics: each row = "at or above start% -> this level/action" (ascending starts)
R9 = [(0,  "green",  "healthy — keep outputs lean"),
      (50, "green+", "note: begin summarizing long threads (Rule 9 first threshold)"),
      (65, "yellow", "trim tool output; reference files instead of re-reading"),
      (80, "orange", "AUTO-SAVEPOINT NOW (checkpoint + push) — then continue or open a new chat"),
      (90, "red",    "HARD STOP — run `wrap` immediately, open a NEW chat, paste the restore line")]
PACING = [(0,  "green",  "on pace"),
          (70, "yellow", "pace — prefer summaries + short replies; avoid big dumps"),
          (85, "orange", "finish critical work; wrap non-essential threads"),
          (95, "red",    "wrap + stop non-essential turns until reset")]

def est_tokens(chars, ratio=CHARS_PER_TOKEN):
    return int(chars / ratio + 0.5)

def _today():
    # Day boundary follows the BOSS timezone (default Asia/Manila = UTC+8),
    # because daily quotas roll over by the user's day, not the sandbox clock.
    off_h = float(os.environ.get("QG_TZ_OFFSET", "8"))
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() + off_h * 3600))

def load(path=STATE):
    try:
        st = json.load(open(path))
    except Exception:
        st = {}
    if st.get("date") != _today():
        st = {"date": _today(), "entries": [], "total_est": 0}
    st.setdefault("entries", [])
    st.setdefault("total_est", 0)
    return st

def save(st, path=STATE):
    st["entries"] = st["entries"][-2000:]
    json.dump(st, open(path, "w"))

def _level(pct, table):
    out = table[0]
    for start, lvl, act in table[1:]:
        if pct >= start:
            out = (start, lvl, act)
        else:
            break
    return out[1], out[2]

def cmd_add(a):
    st = load(a.state)
    chars = a.chars if a.chars else len(_read(a))
    tok = est_tokens(chars, a.ratio)
    st["entries"].append({"t": time.time(), "kind": a.kind, "chars": chars, "est": tok})
    st["total_est"] += tok
    save(st, a.state)
    pct = 100.0 * st["total_est"] / a.daily
    lvl, act = _level(pct, PACING)
    print(json.dumps({"ok": True, "added_est_tokens": tok, "daily_est_total": st["total_est"],
                      "daily_reference": a.daily, "pct_used": round(pct, 2), "level": lvl,
                      "action": act, "note": "LOCAL pacing estimate — not the platform counter"}, indent=1))

def cmd_context(a):
    chars = a.chars if a.chars else len(_read(a))
    tok = est_tokens(chars, a.ratio)
    pct = 100.0 * tok / a.window
    lvl, act = _level(pct, R9)
    print(json.dumps({"ok": True, "context_est_tokens": tok, "window_reference": a.window,
                      "pct_full": round(pct, 1), "level": lvl, "rule9_action": act,
                      "note": "estimate — no exact meter exists; err on the early side"}, indent=1))

def cmd_preflight(a):
    chars = a.chars if a.chars else len(_read(a))
    tok = est_tokens(chars, a.ratio)
    pctw = 100.0 * tok / a.window
    verdict = "SAFE" if pctw < 10 else "HEAVY" if pctw < 30 else "TOO BIG for chat"
    tip = ("safe to paste" if verdict == "SAFE" else
           "consider: phone/PC-side read + summary instead (doctrine Rule 8)" if verdict == "HEAVY" else
           "DO NOT paste — read on phone/PC and bring only a summary (doctrine Rule 8)")
    print(json.dumps({"ok": True, "chars": chars, "est_tokens": tok,
                      "pct_of_window_reference": round(pctw, 1), "verdict": verdict, "tip": tip}, indent=1))

def cmd_report(a):
    st = load(a.state)
    pct = 100.0 * st["total_est"] / a.daily
    lvl, act = _level(pct, PACING)
    by_kind = {}
    for e in st["entries"]:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + e["est"]
    print(json.dumps({"ok": True, "date": st["date"], "turns_logged": len(st["entries"]),
                      "daily_est_total": st["total_est"], "daily_reference": a.daily,
                      "pct_used": round(pct, 2), "level": lvl, "action": act,
                      "by_kind": by_kind,
                      "honesty": "LOCAL pacing record — the real quota counter is server-side and invisible"}, indent=1))

def _read(a):
    if getattr(a, "file", None):
        return open(a.file, encoding="utf-8", errors="replace").read()
    return sys.stdin.read()

def selftest():
    wins, fails = [], []
    def ck(name, cond):
        (wins if cond else fails).append(name)
    ck("est_400chars=100tok", est_tokens(400) == 100)
    ck("est_ratio_override", est_tokens(300, 3.0) == 100)
    s = load("/tmp/qg_selftest.json"); ck("fresh_state", s["total_est"] == 0)
    ck("r9_10pct_green", _level(10, R9)[0] == "green")
    ck("r9_55_note", _level(55, R9)[0] == "green+")
    ck("r9_82_orange", _level(82, R9)[0] == "orange" and "SAVEPOINT" in _level(82, R9)[1])
    ck("r9_95_red", _level(95, R9)[0] == "red" and "wrap" in _level(95, R9)[1])
    ck("pacing_80_yellow", _level(80, PACING)[0] == "yellow")
    ck("pacing_96_red", _level(96, PACING)[0] == "red")
    st = {"date": _today(), "entries": [], "total_est": 0}
    st["total_est"] += est_tokens(8000); ck("budget_accumulates", st["total_est"] == 2000)
    print("SELFTEST %d PASS / %d FAIL" % (len(wins), len(fails)), "" if not fails else fails)
    return 0 if not fails else 1

def main():
    p = argparse.ArgumentParser(description="Zillion quota & context guardrail (estimation + pacing, never circumvention)")
    p.add_argument("--state", default=STATE)
    p.add_argument("--ratio", type=float, default=CHARS_PER_TOKEN, help="chars per token (default 4.0; code ~3.0)")
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="context window reference")
    p.add_argument("--daily", type=int, default=DEFAULT_DAILY, help="daily pacing reference (set to real plan limit when known)")
    p.add_argument("--selftest", action="store_true", help="run the unit self-test and exit")
    sub = p.add_subparsers(dest="cmd")
    a1 = sub.add_parser("add", help="log estimated spend of one turn/tool call (chars via --chars, --file, or stdin)")
    a1.add_argument("--kind", default="turn"); a1.add_argument("--chars", type=int); a1.add_argument("--file")
    a2 = sub.add_parser("context", help="Rule-9 verdict for a given context size (--chars/--file/stdin)")
    a2.add_argument("--chars", type=int); a2.add_argument("--file")
    a3 = sub.add_parser("preflight", help="estimate text BEFORE pasting into chat")
    a3.add_argument("--chars", type=int); a3.add_argument("--file")
    sub.add_parser("report", help="daily pacing report")
    args = p.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.cmd:
        p.print_help(); sys.exit(2)
    {"add": cmd_add, "context": cmd_context, "preflight": cmd_preflight, "report": cmd_report}[args.cmd](args)

if __name__ == "__main__":
    main()
