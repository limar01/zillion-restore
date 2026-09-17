# 🔧 PC tunnel fix kit — one command on the PC

**Why:** the PC lane has no reachable terminal right now (PC absent from the LAN and from all
three MQTT brokers), and its key is from the pre-rotation generation — so even when it boots it
will look dead until the key is refreshed. This kit does the whole repair in one run.

## Run it on the PC (Arch / Omarchy or any Linux)

```bash
bash pc_tunnel_fix.sh "<PASSPHRASE>"
```

It is idempotent and safe to re-run. Steps performed:

1. fetch the trusted gateway URL from the public restore surface (`url.txt`)
2. **refresh the HMAC key** from the phone gateway (keyless bootstrap) → fixes the stale-key fault
3. check deps (`python3`, `paho-mqtt`, `cloudflared`) and locate the local stack
   (`$HOME/Projects/tunnel_bridge` preferred)
4. apply the documented `qwenOM` deploy fixes (paho API call form, `grep --line-buffered`)
5. start `zg.py` on `:8788` + a Cloudflare quick tunnel; capture the new URL
6. verify `/ping` **and** a full HMAC exec round-trip end to end
7. publish the live URL to the bridge as a signed, retained `pc/pres`

Output: `~/arenabridge/pc_tunnel_url.txt` (URL) and `~/arenabridge/pc_tunnel_fix.log` (log).
The key is written only to `~/arenabridge/arenabridge.key` (mode 600) and is never printed —
only its `sha256` fingerprint.

## Remote one-liner (after this script is pushed to the public surface)

```bash
curl -fsSL https://raw.githubusercontent.com/limar01/zillion-restore/main/pc_tunnel_fix.sh | bash -s -- "<PASSPHRASE>"
```

*(The push needs the owner's go-ahead — the phone holds the `github-zr` deploy key and can push it.)*

## Boot-time self-heal (optional, recommended)

Add to the PC's session/boot (systemd user unit or autostart), so the tunnel repairs itself
after a reboot:

```ini
# ~/.config/systemd/user/zillion-pc-tunnel.service
[Unit]
Description=zillion PC tunnel (zg + cloudflared + signed presence)
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=%h/Projects/tunnel_bridge/pc_tunnel_fix.sh %h/.config/zillion/pc_passphrase   # passphrase from a 600 file, never in the unit
Restart=on-failure

[Install]
WantedBy=default.target
```
