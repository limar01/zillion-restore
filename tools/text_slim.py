#!/usr/bin/env python3
"""tools/text_slim.py — COMPRESS-BEFORE-PASTE slimming (v2.3.3)
========================================================================
HONEST SCOPE (doctrine Rule 2 — no pretending):
This tool does NOT touch, reset, or evade the platform quota/context
limits (those are server-side and invisible — see tools/quota_guard.py).
It does the one internet-proven, legitimate workaround for PASTES:
make the text smaller BEFORE it enters the chat, so fewer tokens are
ever spent on it. Reported savings are estimates (chars/ratio), never
exact token counts — no real meter exists.

What it does (deterministic, stdlib-only, no network):
  code  — strip full-line + block comments, collapse blank runs
          (indentation kept; shebang kept; strings may be affected only
          if a whole LINE is a comment-looking string — review output)
  log   — consecutive-duplicate collapse ("×N") + timestamp strip
          (--keep-ts to disable) + blank collapse
  json  — real minify via json.dumps separators (lossless re-serialize)
  html  — HTML -> readable text (tags removed, block structure kept)
  text  — whitespace normalization + blank-run collapse (lightest touch)
  auto  — pick the kind by content heuristics (--kind auto)
  BIG-INPUT GUARD — if the result still exceeds --max-chars (default
  12000), keep head 60% + tail 40% on LINE BOUNDARIES with an explicit
  "N chars omitted" marker (head/tail is how flaky tool output is tamed).
  The original file is NEVER modified.

Output contract:
  STDOUT = the slimmed text (pipeable). STDERR = the human report
  (sizes, est. savings, SAFE/HEAVY/TOO BIG verdict vs --window).
  Exit code: 0 = SAFE/HEAVY · 2 = still TOO BIG (use Rule-8 phone-side
  read + summary instead) · 1 = input error.

Verdict bands (share of the reference window, est): matches
quota_guard preflight — SAFE < 10% · HEAVY < 30% · else TOO BIG.
Savings claims vs 3rd-party tools (60-80% on logs) vary by input —
benchmarks in chat reports must label "est".
"""
import argparse, json, sys, re
from html.parser import HTMLParser

CHARS_PER_TOKEN = 4.0          # est heuristic (code denser ~3.0) — --ratio
DEFAULT_WINDOW  = 128_000      # reference window — --window
DEFAULT_MAX     = 12_000       # post-slim head/tail crop — --max-chars

def est_tokens(chars, ratio=CHARS_PER_TOKEN):
    return int(chars / ratio + 0.5)

def detect(text):
    s = text.strip()
    if s[:1] in "{[":
        try:
            json.loads(s)
            return "json"
        except Exception:
            pass
    if (re.search(r"</(html|body|div|span|p|table|tr|td)\s*>", text, re.I)
            or re.search(r"<(html|body|div)[\s>]", text, re.I)):
        return "html"
    ts = re.compile(r"^\s*(\[?\d{4}-\d{2}-\d{2}[T ]\d{2}:|\d{2}:\d{2}:\d{2}|\b(INFO|ERROR|WARN(?:ING)?|DEBUG|TRACE|FATAL)\b)", re.M)
    if len(ts.findall(text)) >= 3:
        return "log"
    # markdown/prose must NEVER hit the code slimmer (# headings look like
    # Python comments) — markdown dominance wins over code markers.
    md = re.findall(r"^(#{1,6}\s|\s*[-*•]\s|>\s|\||\d+\.\s)", text, re.M)
    code = re.findall(r"^\s*(import |from \S+ import |def |class \w+|function |const |let |var |public |private |static |return |if \(|for \(|while \(|// |/\*)|;$", text, re.M)
    if len(md) >= 4 and len(md) >= len(code):
        return "text"
    if len(code) >= 4:
        return "code"
    return "text"

def _blankcollapse(lines):
    out, blank = [], False
    for ln in lines:
        if ln.strip() == "":
            if not blank:
                out.append("")
            blank = True
        else:
            out.append(ln)
            blank = False
    while out and out[0] == "": out.pop(0)
    while out and out[-1] == "": out.pop()
    return out

def slim_code(text):
    out, in_block = [], False
    for ln in text.split("\n"):
        s = ln.lstrip()
        if in_block:
            if "*/" in s:
                in_block = False
                s = s.split("*/", 1)[1]
                if not s.strip():
                    continue
            else:
                continue
        elif s.startswith("/*"):
            if "*/" in s[2:]:
                if not s.split("*/", 1)[1].strip():
                    continue
            else:
                in_block = True
                continue
        elif s.startswith(("#", "//", "<!--", "*")) and not s.startswith("#!"):
            continue
        out.append(ln.rstrip())
    return "\n".join(_blankcollapse(out))

_LOG_TS = re.compile(
    r"^\s*\[?(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?|"
    r"\d{2}:\d{2}:\d{2}(?:\.\d+)?|\d{10,13})\]?\s*")

def slim_log(text, strip_ts=True):
    lines, prev, count = [], None, 0
    def flush():
        if prev is not None:
            lines.append(prev + (f"  ×{count}" if count > 1 else ""))
    for raw in text.split("\n"):
        norm = _LOG_TS.sub("", raw).rstrip() if strip_ts else raw.rstrip()
        if norm == prev:
            count += 1
        else:
            flush()
            prev, count = norm, 1
    flush()
    return "\n".join(_blankcollapse(lines))

def slim_json(text):
    try:
        return json.dumps(json.loads(text), separators=(",", ":"))
    except Exception:
        return slim_text(text)  # malformed JSON -> safest fallback

class _ToText(HTMLParser):
    BLOCK = {"p","div","br","li","tr","table","section","article","header","footer",
             "h1","h2","h3","h4","h5","h6","ul","ol","pre","blockquote","nav","form"}
    def __init__(self):
        super().__init__()
        self.buf = []
    def handle_data(self, d):
        self.buf.append(d)
    def handle_endtag(self, t):
        if t in self.BLOCK:
            self.buf.append("\n")
    def text(self):
        return "".join(self.buf)

def slim_html(text):
    p = _ToText()
    try:
        p.feed(text)
    except Exception:
        pass
    out = [re.sub(r"[ \t]+", " ", ln).rstrip() for ln in p.text().split("\n")]
    return "\n".join(_blankcollapse(out))

def slim_text(text):
    out = [re.sub(r"[ \t]{2,}", " ", ln).rstrip() for ln in text.split("\n")]
    return "\n".join(_blankcollapse(out))

def sandwich(text, max_chars):
    """Head 60% + tail 40% on line boundaries, explicit omission marker.
    This is the 'tame the firehose' pattern for oversized output."""
    if len(text) <= max_chars:
        return text, 0
    if max_chars < 400:
        max_chars = 400
    head_n = int(max_chars * 0.6)
    tail_n = max_chars - head_n
    head = text[:text.find("\n", head_n) if text.find("\n", head_n) != -1 else head_n]
    tail_start = max(len(text) - tail_n, len(head))
    nl = text.find("\n", tail_start)
    tail = text[nl + 1:] if nl != -1 else text[tail_start:]
    omitted = len(text) - len(head) - len(tail)
    marker = f"\n…[ text_slim: {omitted} chars (~{est_tokens(omitted)} tok est) omitted — full original kept on device ]…\n"
    return head + marker + tail, omitted

def verdict(tok, window):
    pct = 100.0 * tok / window
    if pct < 10:  return "SAFE", "safe to paste", pct
    if pct < 30:  return "HEAVY", "spend wisely — prefer device-side read + summary (Rule 8) if the pace is hot", pct
    return "TOO BIG", "DO NOT paste — Rule-8 device-side read + summary, or --max-chars smaller", pct

def main():
    p = argparse.ArgumentParser(description="text_slim — compress text BEFORE pasting into chat (never circumvents limits)")
    p.add_argument("pos_file", nargs="?", help="file to slim (or stdin)")
    p.add_argument("--file", dest="opt_file", help="file to slim (alt to positional)")
    p.add_argument("--kind", default="auto", choices=["auto", "code", "log", "json", "html", "text"])
    p.add_argument("--max-chars", type=int, default=DEFAULT_MAX, help="post-slim head/tail crop (default 12000; 0 = no crop)")
    p.add_argument("--ratio", type=float, default=CHARS_PER_TOKEN, help="chars per token est (default 4.0; code ~3.0)")
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="reference context window")
    p.add_argument("--keep-ts", action="store_true", help="log kind: keep timestamps")
    p.add_argument("--selftest", action="store_true", help="run unit self-test and exit")
    a = p.parse_args()
    if a.selftest:
        sys.exit(selftest())
    src = a.opt_file or a.pos_file
    try:
        raw = open(src, encoding="utf-8", errors="replace").read() if src else sys.stdin.read()
    except Exception as e:
        print(f"text_slim: cannot read input: {e}", file=sys.stderr)
        sys.exit(1)
    kind = detect(raw) if a.kind == "auto" else a.kind
    slim = {"code": slim_code, "json": slim_json, "html": slim_html, "text": slim_text}.get(kind)
    out = slim_log(raw, strip_ts=not a.keep_ts) if kind == "log" else slim(raw)
    cropped = False
    if a.max_chars:
        out2, omitted = sandwich(out, a.max_chars)
        cropped = omitted > 0
        out = out2
    sys.stdout.write(out + ("" if out.endswith("\n") else "\n"))
    in_tok, out_tok = est_tokens(len(raw), a.ratio), est_tokens(len(out), a.ratio)
    saved = (100.0 * (len(raw) - len(out)) / len(raw)) if raw else 0.0
    band, tip, pct = verdict(out_tok, a.window)
    print(f"text_slim v2.3.3 · kind={kind}" + (" (auto)" if a.kind == "auto" else ""), file=sys.stderr)
    print(f"in   {len(raw):,} chars  ~{in_tok:,} tok (est @ratio {a.ratio})", file=sys.stderr)
    print(f"out  {len(out):,} chars  ~{out_tok:,} tok (est)   −{saved:.1f}% (est)" + ("  [head/tail crop]" if cropped else ""), file=sys.stderr)
    print(f"window {pct:.1f}% of {a.window:,} ref → {band}: {tip}", file=sys.stderr)
    sys.exit(2 if band == "TOO BIG" else 0)

def selftest():
    wins, fails = [], []
    def ck(name, cond):
        (wins if cond else fails).append(name)
    # 1 json minify, lossless
    pretty = '{\n  "a": 1,\n  "b": [1, 2, 3, {"c": "d"}],\n  "e": "keep me"\n}\n'
    mini = slim_json(pretty)
    ck("json_minify_lossless", json.loads(mini) == json.loads(pretty) and len(mini) < len(pretty))
    # 2 code: comments out, indentation kept
    code = '#!/usr/bin/env python3\n# top comment\n\ndef f():\n    x = 1  # keep line\n    // js-style comment\n    /* block\n       mid\n       end */\n    return x\n\n\n\nprint(f())\n'
    slim = slim_code(code)
    ck("code_comments_out", "# top comment" not in slim and "block" not in slim and "mid" not in slim)
    ck("code_indent_shebang", slim.startswith("#!") and "    x = 1" in slim and "return x" in slim)
    # 3 log: dedupe + ts strip
    log = "2026-09-18T10:00:01 INFO boot ok\n2026-09-18T10:00:02 INFO boot ok\n2026-09-18T10:00:03 INFO boot ok\n2026-09-18T10:00:04 ERROR disk slow\n"
    s = slim_log(log)
    ck("log_dedupe_ts", "×3" in s and "disk slow" in s and s.count("boot ok") == 1 and "10:00:01" not in s)
    # 4 log keep-ts
    s2 = slim_log(log, strip_ts=False)
    ck("log_keep_ts", "×3" not in s2)
    # 5 html -> text
    h = slim_html("<html><body><h1>Hello Boss</h1><p>Line one</p><p>Line two</p></body></html>")
    ck("html_text", "Hello Boss" in h and "Line two" in h and "<" not in h)
    # 6 sandwich respects budget
    big = "\n".join("row %d payload" % i for i in range(3000))
    sw, omitted = sandwich(big, 400)
    ck("sandwich", omitted > 0 and len(sw) <= 400 + 120 and "omitted" in sw)
    # 7 detect kinds
    ck("detect", detect(pretty) == "json" and detect(log) == "log" and
       detect(code) == "code" and detect("<div>x</div><p>y</p>") == "html" and
       detect("a simple sentence about nothing in particular.") == "text")
    # 8 markdown is PROSE, never code (# headings must survive)
    md = "# Title\n\ntext\n\n## Sub\n- one\n- two\n- three\n### More\n|a|b|\n1. x\n2. y\n"
    ck("detect_markdown_as_text", detect(md) == "text")
    # 9 text blank collapse
    ck("text_blanks", slim_text("a\n\n\n\n\nb") == "a\n\nb")
    # 10 markdown content untouched by text slimmer
    ck("markdown_safe", slim_text(md).startswith("# Title") and "### More" in slim_text(md))
    print("SELFTEST %d PASS / %d FAIL" % (len(wins), len(fails)), "" if not fails else fails)
    return 0 if not fails else 1

if __name__ == "__main__":
    main()
