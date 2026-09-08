#!/data/data/com.termux/files/usr/bin/sh
# supervisor.sh v4 (2026-09-09): atomic lock (F12) + AB_CMD_TIMEOUT=120 sa worker (F4)
# + start_zg 2-retry bago kill (F12 churn fix)
cd "$HOME/zillion_pw" || exit 1
log="$HOME/zillion_pw/supervisor.log"
LOCK="$HOME/zillion_pw/.supervisor.lock"
mkdir "$LOCK" 2>/dev/null || { echo "$(date) supervisor already running (lock held) -- exit" >> "$log"; exit 0; }
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
echo "$(date) supervisor v4 started (pid $$)" >> "$log"
while :; do
  start_worker
  start_zg
  start_beacon
  start_helpers
  sleep 30
done
