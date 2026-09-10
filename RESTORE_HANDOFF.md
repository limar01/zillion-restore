# Required private session handoff

The owner selected **private summarized history**. Do not copy private handoff/history into this public repository.

## Required restore sequence

1. Read `MEMORY_CORE.md`, complete GATE 0 and the documented tunnel/bridge restore. Do not infer project progress from an old chat or from connection success.
2. On the PHONE, use the existing private `tunnel-adb` checkout at `~/Projects/workspace/zillion-doctrine/tunnel-adb`. Fetch and fast-forward its `main` branch through the registered `github-ta` deploy key. Preserve dirty/pending local work; do not reset or force-push it.
3. If that checkout is absent, clone `git@github-ta:limar01/tunnel-adb.git` on the PHONE, not into the cloud relay. A sparse checkout of `/MEMORY_CORE.md`, `/RESTORE_HANDOFF.md`, `/memory/CURRENT_HANDOFF.md`, `/memory/session_logs/`, and `/memory/tools/` avoids retrieving unrelated private material.
4. Read `memory/CURRENT_HANDOFF.md` and only the last few relevant entries of the latest monthly journal under `memory/session_logs/`. Do not load the whole archive into chat context.
5. Verify the active project's actual branch/commit, dirty files, artifact hashes, and storage destination before resuming. The handoff is a state record, not permission to replay historical commands. Current owner instructions and safeguards still apply.

## Checkpoint routine

On the phone, run `python3 ~/Projects/workspace/zillion-doctrine/tunnel-adb/memory/tools/checkpoint.py` with a JSON object on stdin containing `event_id`, `summary`, and `handoff` (sanitized Markdown body). The helper appends the monthly log, updates the compact current view, commits only those files, pushes with the phone deploy key, checks the remote commit, and mirrors these memory files to the phone restore pack and the PRIVATE SanDisk mirror.

Update after meaningful milestones, before long/risky operations or a handoff/new chat, and before ending an active-work turn. If a push fails, stop long/risky project work and report that the checkpoint is only local. Never claim it is GitHub-saved without verification.

## Recovery copies and limits

Phone mirror: `~/zillion_pw/_pack/memory/`.
Private SD mirror: `/storage/BDD5-1822/gitrepo/tunnel-adb/memory/`.
The public SD Git checkout is separately `/storage/BDD5-1822/gitrepo/zillion-restore`; private history MUST NOT be copied there.

A credential-free strict connection adapter is preserved privately as `memory/tools/restore_session.py`. It is a cloud-relay helper to restore to `/home/user/restore_session.py`, not a phone application. It reads the separately protected local key and must be activated in each new client process. Never place the key in code/history. Required connection-client files are the only cloud-side runtime exception; project processing remains phone-first.

This is an agent-maintained checkpoint workflow, not a background recorder of inactive chats. Do not promise access to unseen conversations or an exact context percentage without a reliable meter.
