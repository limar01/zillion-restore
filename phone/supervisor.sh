#!/data/data/com.termux/files/usr/bin/sh
# supervisor.sh v4.2 (2026-09-09): v4 + STALE-LOCK RECOVERY (fixed).
# v4.1 BUG (caught in live test 08:17): pid file is written INSIDE the lock dir,
# so a SIGKILL'd v4.1 holder leaves a NON-EMPTY lock -> rmdir fails -> recovery
# dead-ends at "lock held -- exit". v4.2: rm -f "$LOCK/pid" (targeted, known file
# only) before rmdir.
# BUG FIXED: v4 lock = mkdir + trap rmdir. SIGKILL (Android idle-kill / app close)
# or REBOOT skips the trap -> lock dir persists -> every later start (Termux:Boot
# boot chain, manual start_all) exits "lock held" forever. Incident 2026-09-09:
# supervisor 13613 (lock 05:10) killed ~06:06; phone rebooted ~06:58; all starts
# 07:00-07:42 blocked by the stale lock; stack dead until manual worker start.
# FIX: on lock-held, verify the holder is actually alive (pid + cmdline anti-reuse);
# old-format locks (no pid file) are stale after 10 min. Clear once, retry, else exit.
cd "$HOME/zillion_pw" || exit 1
log="$HOME/zillion_pw/supervisor.log"
LOCK="$HOME/zillion_pw/.supervisor.lock"

try_lock() {
  mkdir "$LOCK" 2>/dev/null && return 0
  holder=$(cat "$LOCK/pid" 2>/dev/null)
  stale=0
  if [ -z "$holder" ]; then
    # old-format lock (no pid file): stale if older than 10 min
    [ -n "$(find "$LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ] && stale=1
  elif ! kill -0 "$holder" 2>/dev/null; then
    stale=1                      # holder pid dead
  elif ! grep -qa 'supervisor\.sh' "/proc/$holder/cmdline" 2>/dev/null; then
    stale=1                      # pid reused by another process
  fi
  if [ "$stale" = 1 ]; then
    echo "$(date) clearing STALE lock (holder='${holder:-none}')" >> "$log"
    rm -f "$LOCK/pid" 2>/dev/null      # v4.2: lock dir must be empty for rmdir
    rmdir "$LOCK" 2>/dev/null
    mkdir "$LOCK" 2>/dev/null && return 0
  fi
  return 1
}

if ! try_lock; then
  echo "$(date) supervisor already running (lock held) -- exit" >> "$log"
  exit 0
fi
echo "$$" > "$LOCK/pid" 2>/dev/null
trap 'rmdir "$LOCK" 2>/dev/null' EXIT INT TERM
start_worker() {
  if ! pgrep -f '^python3 .*/arenabridge/worker\.py$|^python3 worker\.py$' >/dev/null 2>&1; then
    (cd "$HOME/arenabridge" && nohup env ZILLION_LANE=cp AB_CMD_TIMEOUT=120 python3 "$HOME/arenabridge/worker.py" >> "$HOME/arenabridge/worker.log" 2>&1 </dev/null &)
    echo "$(date) start mqtt worker (AB_CMD_TIMEOUT=120)" >> "$log"
  fi
}
start_zg() {
  ok=0
  for i in 1 2; do
    if curl -fsS --max-time 4 http://127.0.0.1:8788/ping >/dev/null 2>&1; then ok=1; break; fi
    sleep 2
  done
  if [ "$ok" = 0 ]; then
    for p in $(pgrep -f '^python3 .*zg\.py$' 2>/dev/null); do kill "$p" 2>/dev/null || true; done
    nohup env ZG_PORT=8788 python3 "$HOME/zillion_pw/zg.py" >> "$HOME/zillion_pw/zg.log" 2>&1 </dev/null &
    echo "$(date) start zg:8788" >> "$log"
  fi
}
start_beacon() {
  if ! pgrep -f '^python3 .*/zillion_pw/ph_beacon\.py$|^python3 ph_beacon\.py$' >/dev/null 2>&1; then
    nohup python3 "$HOME/zillion_pw/ph_beacon.py" >> "$HOME/zillion_pw/beacon.log" 2>&1 </dev/null &
    echo "$(date) start beacon" >> "$log"
  fi
}
start_helpers() {
  if ! pgrep -f '^sh .*/zillion_pw/cf_retry\.sh$|^sh ./cf_retry\.sh$' >/dev/null 2>&1; then
    nohup sh "$HOME/zillion_pw/cf_retry.sh" >> "$HOME/zillion_pw/cf_retry.out" 2>&1 </dev/null &
    echo "$(date) start cf retry" >> "$log"
  fi
  if ! pgrep -f '^sh .*/zillion_pw/fallback_retry\.sh$|^sh ./fallback_retry\.sh$' >/dev/null 2>&1; then
    nohup sh "$HOME/zillion_pw/fallback_retry.sh" >> "$HOME/zillion_pw/fallback_retry.out" 2>&1 </dev/null &
    echo "$(date) start fallback retry" >> "$log"
  fi
}
command -v termux-wake-lock >/dev/null 2>&1 && timeout 5 termux-wake-lock >/dev/null 2>&1 || true
echo "$(date) supervisor v4.2 started (pid $$)" >> "$log"
while :; do
  start_worker
  start_zg
  start_beacon
  start_helpers
  sleep 30
done
