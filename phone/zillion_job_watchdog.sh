#!/data/data/com.termux/files/usr/bin/sh
# zillion job watchdog — 15-min WorkManager resurrection (v2, 2026-09-09)
# ONE-SHOT: check supervisor; if missing, start_all brings the stack back.
# MUST ALWAYS EXIT — a job script that never finishes blocks future job runs.
# v4.2 supervisor self-heals any stale lock on that restart.
LOG="$HOME/zillion_pw/job_watchdog.log"
if ! pgrep -f "^sh .*/zillion_pw/supervisor\.sh$" >/dev/null 2>&1; then
  bash "$HOME/zillion_pw/start_all.sh" >> "$LOG" 2>&1
  echo "[job-watchdog] $(date) stack was missing - start_all run (resurrect)" >> "$LOG"
  # keep log small
  if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 100 ]; then
    tail -n 50 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
  fi
fi
