#!/data/data/com.termux/files/usr/bin/sh
set -u
cd "$HOME/zillion_pw" || exit 1
command -v termux-wake-lock >/dev/null 2>&1 && timeout 5 termux-wake-lock >/dev/null 2>&1 || true
if ! pgrep -f '^sh .*/zillion_pw/supervisor\.sh$' >/dev/null 2>&1; then
  nohup sh "$HOME/zillion_pw/supervisor.sh" >> "$HOME/zillion_pw/supervisor.out" 2>&1 </dev/null &
fi
echo "Zillion phone supervisor armed"
