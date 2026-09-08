#!/data/data/com.termux/files/usr/bin/sh
# cf_retry.sh v3 (2026-09-09): v2 logic + cf.log rotation per attempt (F7 — unbounded growth fix)
cd "$HOME/zillion_pw" || exit 1
delay=300
maxdelay=3600
crash=0
while :; do
  if pgrep -f 'cloudflared tunnel.*127\.0\.0\.1:8788' >/dev/null 2>&1; then
    crash=0
    sleep 60
    continue
  fi
  # F7: rotate log bago bago attempt (keep 1 generation)
  [ -f cf.log ] && mv cf.log cf.log.1 2>/dev/null
  echo "=== ATTEMPT $(date) delay=$delay crash=$crash ===" >> cf_retry.log
  cloudflared tunnel --protocol http2 --edge-ip-version 4 --url http://127.0.0.1:8788 >> cf.log 2>&1
  rc=$?
  echo "$(date) exit=$rc; crash=$crash" >> cf_retry.log
  if tail -n 20 cf.log 2>/dev/null | grep -q '429 Too Many Requests'; then
    delay=$(( delay * 2 )); [ "$delay" -gt "$maxdelay" ] && delay="$maxdelay"
    crash=0
    sleep "$delay"
  else
    crash=$((crash+1))
    if [ "$crash" -ge 3 ]; then
      sleep "$delay"
      delay=$(( delay * 2 )); [ "$delay" -gt "$maxdelay" ] && delay="$maxdelay"
      crash=0
    else
      sleep 10
    fi
  fi
done
