#!/data/data/com.termux/files/usr/bin/sh
cd "$HOME/zillion_pw" || exit 1
geturl() { grep -Eo 'https://[a-zA-Z0-9-]+\.lhr\.life' fallback.log 2>/dev/null | tail -1; }
killssh() {
  for p in $(pgrep -f '^ssh .*localhost\.run$' 2>/dev/null); do kill "$p" 2>/dev/null || true; done
}
while :; do
  url=$(geturl)
  if pgrep -f '^ssh .*localhost\.run$' >/dev/null 2>&1 && [ -n "$url" ] && curl -fsS --max-time 8 "$url/ping" >/dev/null 2>&1; then
    sleep 60
    continue
  fi
  killssh
  : > fallback.log
  nohup ssh -T -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -R 80:127.0.0.1:8788 nokey@localhost.run >fallback.log 2>&1 </dev/null &
  echo "$(date) fallback restarted" >> fallback_retry.log
  sleep 20
  url=$(geturl)
  if [ -z "$url" ] || ! curl -fsS --max-time 8 "$url/ping" >/dev/null 2>&1; then
    killssh
    sleep 120
  else
    sleep 60
  fi
done
