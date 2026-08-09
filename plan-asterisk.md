# Asterisk Configuration Plan

## Goal
Asterisk runs on the Raspberry Pi, registers to the FritzBox as an IP phone,
and originates calls to the analog phone. When answered, it plays a pre-rendered
voice instruction from a WAV file.

---

## Prerequisites
- FritzBox plan completed: SIP credentials and analog phone extension known
- Arch Linux ARM installed, Pi reachable on the FritzBox network
- Asterisk installed: `pacman -S asterisk`

---

## Step 1 — Install and enable Asterisk
```bash
pacman -S asterisk
systemctl enable asterisk
```
Config lives in `/etc/asterisk/`. Default config ships with many sample files —
most can be left alone. We only touch: `pjsip.conf`, `extensions.conf`.

---

## Step 2 — Configure pjsip.conf
File: `/etc/asterisk/pjsip.conf`

Replace the contents (or append below any existing transport block):

```ini
; Transport
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0

; AoR — where to send traffic for this endpoint
[fritzbox]
type=aor
contact=sip:fritz.box

; Auth credentials (match FritzBox IP phone account)
[fritzbox-auth]
type=auth
auth_type=userpass
username=620          ; internal number from FritzBox
password=SECRET_SIP   ; password set in FritzBox

; Endpoint — the Pi's identity on the FritzBox network
[fritzbox]
type=endpoint
transport=transport-udp
context=fluxus        ; dialplan context (extensions.conf)
disallow=all
allow=ulaw
allow=alaw
outbound_auth=fritzbox-auth
aors=fritzbox
from_user=620
from_domain=fritz.box

; Registration — Pi registers to FritzBox as an IP phone
[fritzbox-reg]
type=registration
transport=transport-udp
outbound_auth=fritzbox-auth
server_uri=sip:fritz.box
client_uri=sip:620@fritz.box
contact_user=620
retry_interval=30
```

Adjust `username`, `password`, and `620` to match your FritzBox setup.

---

## Step 3 — Configure extensions.conf
File: `/etc/asterisk/extensions.conf`

```ini
[fluxus]
; Called when the analog phone is picked up.
; SOUND is set by the trigger script via AMI — either a file on the audio stick
; or the fallback path when the stick is absent.
exten => _X.,1,NoOp(Fluxus call started — playing ${SOUND})
 same => n,Wait(1)
 same => n,Playback(${SOUND})
 same => n,Hangup()
```

The `[fluxus]` context handles the call once the analog phone picks up.
The trigger script originates the call via AMI and sets `${SOUND}` to the audio
file path — see Step 6.

---

## Step 4 — Enable AMI (Asterisk Manager Interface)
The Python trigger script needs AMI to originate calls without SSH.

File: `/etc/asterisk/manager.conf`

```ini
[general]
enabled=yes
port=5038
bindaddr=127.0.0.1   ; local only, no network exposure

[fluxus]
secret=kx9Qm4vTpL2w
deny=0.0.0.0/0.0.0.0
permit=127.0.0.1/255.255.255.0
read=all
write=originate
```

---

## Step 5 — Pre-render instruction audio
Audio files live on the **audio USB stick** (mounted at `/mnt/audio/`), not on
the system stick. This makes updates easy: unmount, take the stick to any
computer, swap the WAVs, plug back in.

Generate files on any machine with espeak-ng, then copy to the stick:

```bash
espeak-ng -v de -s 110 "Geh zur roten Tür und klopfe dreimal." \
  -w /tmp/instruction_01_raw.wav

# convert to 8 kHz mono (required by Asterisk / FritzBox codec)
sox /tmp/instruction_01_raw.wav \
  -r 8000 -c 1 -e signed-integer -b 16 \
  /path/to/audio-stick/instruction_01.wav

# repeat for each instruction
```

File naming: `instruction_01.wav`, `instruction_02.wav`, … any count.
The trigger script discovers them automatically by scanning `/mnt/audio/`.

The **fallback audio** (played when the stick is absent) is pre-rendered once
onto the system stick — see plan-raspberry-pi.md Part 8d.

---

## Step 6 — Python trigger script
Source: [`deploy/fluxus-trigger.py`](deploy/fluxus-trigger.py)
Deploy to: `/usr/local/bin/fluxus-trigger.py`

---

## Step 7 — systemd unit for the trigger script
Source: [`deploy/fluxus-trigger.service`](deploy/fluxus-trigger.service)
Deploy to: `/etc/systemd/system/fluxus-trigger.service`

```bash
systemctl enable fluxus-trigger
systemctl start fluxus-trigger
```

---

## Step 8 — Verify registration
```bash
asterisk -rx "pjsip show registrations"
# should show: fritzbox-reg  Registered
```

Test a manual call:
```bash
asterisk -rx "channel originate PJSIP/**1@fritzbox application Playback /var/lib/asterisk/sounds/fluxus/instruction_01"
# analog phone should ring
```

---

## Notes
- Audio file paths in `Playback()` omit the `.wav` extension — Asterisk adds it
- If registration fails, check fritz.box resolves: `ping fritz.box`
- FritzBox 7270 only supports ulaw/alaw — no opus or g722
- On reboot the Pi waits for DHCP before Asterisk starts; add `After=network-online.target` to the Asterisk unit if registration is slow
