# UPDATE v1.3.8 — DEPLOY-KEY VERIFIED RESTORE (2026-09-09)

## Ano ang nangyari
- Sa live session, na-discover na ang PAREHONG phone deploy keys (`github-zr`, `github-ta`) ay **hindi registered** sa GitHub (`ssh -T` → `Permission denied (publickey)`), kahit na ang huling push sa lane (`f6546d4`, url.txt, 02:50:24 +0800) ay successful gamit ang `github-zr`.
- Na-verify: keys nasa phone (`~/.ssh/id_ed25519_zr` / `_ta`, mode 600), aliases tama sa `~/.ssh/config`, walang ibang credentials saan man (walang `~/.git-credentials`, walang `credential.helper`, walang `gh`, PAT retired).
- Isang embedded (patay nang) PAT ang nakita sa `~/termux-memory-public/.git/config` (401 Bad credentials) — **scrubbed** (`git remote set-url` → malinis na URL).

## Boss action (one-time, 2026-09-09)
Idinagdag ni Boss ang PAREHONG pubkeys bilang **deploy keys (write access)**:
- `zillion-restore`: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGbHNVokuTISzCU/KOn8y+745k1PeXTzA0+LaDZtqVty phone-zillion-restore`
- `tunnel-adb`: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAl8mUQkcb1J86yJVHDPsQRpcXI/5zyJyuO2vVL3q18y phone-tunnel-adb`

## Verification (raw evidence)
```
ssh -T github-zr → Hi limar01/zillion-restore! You've successfully authenticated...
ssh -T github-ta → Hi limar01/tunnel-adb! You've successfully authenticated...
push probe: clone → throwaway branch → PUSH_OK → REMOTE_HAS_BRANCH cb7be69c6114 → DELETE_OK
```

## Mga pagbabago sa doctrine (MEMORY_CORE v1.3.8)
1. **LIST C step 6c — DEPLOY-KEY VERIFY:** post-key, phone exec `ssh -T github-zr` + `github-ta`; kung denied → remediation (pubkeys nasa PUSH SETUP section; ipakita kay Boss para i-re-add). Hindi restore-blocker, mandatory i-report.
2. **KEY DELIVERY Fallback 1 (concrete):** private vault clone via phone exec `git@github-ta:limar01/tunnel-adb.git` o SD tier — sandbox keyless by design.
3. **PUSH SETUP v1.3.8 VERIFIED:** evidence + remediation playbook + pubkeys (public-safe) nasa core.
4. **OPERATIVE RULE 14 — CREDENTIAL HYGIENE:** bawal embedded userinfo sa git remotes; nakita = scrub + report.
5. **Sync protocol:** push `github-zr` + push `github-ta` + cp `_pack` + cp SD working tree.

## Sync status ng core na ito
- GitHub public (`zillion-restore`): pushed via `github-zr` (ang core na ito mismo ang proof ng lane).
- GitHub private (`tunnel-adb`): pushed via `github-ta`.
- Phone `_pack`: cp done.
- SD working tree: cp done.
