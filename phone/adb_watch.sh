#!/data/data/com.termux/files/usr/bin/sh
# adb_watch.sh v2 (2026-09-09): full-range scan 1024-65535 (F10)
END=$(( $(date +%s) + 480 ))
: > ~/zillion_pw/adb_watch.log
while [ $(date +%s) -lt $END ]; do
  PORTS=$(python3 - << 'P'
import socket
from concurrent.futures import ThreadPoolExecutor
def tp(p):
    s=socket.socket(); s.settimeout(0.04)
    try:
        s.connect(('127.0.0.1',p)); return p
    except Exception: return None
    finally:
        try: s.close()
        except Exception: pass
o=[]
with ThreadPoolExecutor(max_workers=500) as ex:
    for r in ex.map(tp, range(1024,65536)):
        if r: o.append(r)
print(' '.join(map(str,o)))
P
)
  for P in $PORTS; do
    [ "$P" = 5037 ] && continue
    [ "$P" = 8788 ] && continue
    adb connect 127.0.0.1:$P >/dev/null 2>&1
  done
  D=$(adb devices 2>/dev/null | awk -F'\t' '$2=="device"{print $1}' | head -1)
  if [ -n "$D" ]; then
    echo "$(date '+%H:%M:%S') CONNECTED $D" >> ~/zillion_pw/adb_watch.log
    echo "${D##*:}" > ~/zillion_pw/_adb_ports.txt
    adb shell getprop ro.product.model >> ~/zillion_pw/adb_watch.log 2>&1
    exit 0
  fi
  sleep 3
done
echo "$(date '+%H:%M:%S') TIMEOUT" >> ~/zillion_pw/adb_watch.log
