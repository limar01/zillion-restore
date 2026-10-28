# MCP — REA analysis surface (optional)

`morluto/rea` via the `rea-agents` npm package. Pinned, opt-in, privileged. **No restore path depends on it.**

## Registration

Repo root `.mcp.json`:

```json
{
  "mcpServers": {
    "rea": {
      "command": "npx",
      "args": ["-y", "rea-agents@6.8.0", "mcp"],
      "env": { "REA_APKTOOL_COMMAND": "apktool" }
    }
  }
}
```

Agents that read `.mcp.json` (Claude Code, Codex, Cursor, Gemini CLI, Grok Build) pick this up
automatically. Others: `npx rea-agents@6.8.0 mcp add --agent <name>`.

## Verified state (2026-10-28)

| Check | Result |
|---|---|
| stdio initialize | ok · protocol `2025-11-25` · `rea@6.8.0` |
| `tools/list` | **229 tools**, 6 prompts, no missing/unexpected/duplicates |
| catalog digest | `fe938a7c6eba3763b22ae2022de76dc4a7812d35d86f1d4efd36b9962b04da0b` |
| `rea mcp doctor` | `healthy: true`, adapter `production-stdio` |
| Node required | ≥ 22.23.4 (hard engine constraint) |
| apktool | required for APK work (`REA_APKTOOL_COMMAND`) |

## Requirements

- **Node ≥ 22.23.4.** Older Node fails at engine check.
- **apktool** for `decode-android-resources` / `inspect-android-*`.
- **Ghidra / Hopper / IDA / Kuna** for deep native decompilation. Absent by default; without one,
  engine-backed tools return `capability_unavailable` — by design, not a bug.

## Entry-point trap

`rea analyze <file.apk>` fails: Ghidra and Hopper import **executables**, not **archives**. For an APK use
`decode-android-resources`, `inspect-android-package`, `inspect-apk-signature`, `inspect-android-class`.

## Security posture

REA is a **debugger-class** tool, not a linter:

- `debug-with-gdb`, `debug-with-rizin`, `capture-process`, pcap capture, `inspect-adb-*` and adb exec
  are all in the toolset.
- **Never** point it at a Sacred-Scope target (GCash / DCIM) or a key-bearing session. Scratch
  workspace only.
- **Supply chain:** install only from `morluto/rea`, `rea.tools`, or npm `rea-agents`. The upstream
  README itself warns about lookalike repositories — a signal it is impersonation bait.
- **Pin the version.** `@latest` on a 49 MB package that launches decompilers is not a risk worth taking.
- Star count is adoption, not audit.

## Evidence discipline

Every REA result carries `confidence` (`observed` vs inferred), a provider id + version, an
`evidence_id` hash, and an explicit `limitations[]`. **Quote the limitations when reporting** — e.g.
`inspect-apk-signature` does *not* verify signatures cryptographically; it reports what the APK
declares. This matches the doctrine's existing rule: claim only what you can show.

## What it was actually used for here

Verifying `apk/termux-boot_1000.apk`. See the 🔎 SHIPPED-BINARY VERIFICATION section of
`MEMORY_CORE.md` for the pinned hash and manifest facts.
