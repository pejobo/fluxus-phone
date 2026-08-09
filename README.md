Fluxus-Phone

An old analog phone, randomly ringing. You pick up the handle and a voice speaking gives you instructions.

How it works

The hardware consists of available scrap parts: An old FritzBox 7270, a Raspberry Pi 3B, an old anlog phone, an RJ45 adapter, an old charger for the Raspberry Pi.
And all the cables. It's all wired together. No internet access, since the setup is movable. Plug & play.

The Software: Raspberry Pi OS Lite (64-bit) on an SD card, auto-starting Asterisk and a Python trigger script via systemd.

## Audio USB stick

Audio instructions live on a separate FAT32 USB stick (label: `FLUX-PHON`).
The stick is hot-pluggable; mounting and conversion happen automatically on plug.

### Stick layout

```
ORIGINAL/
    anweisung_01.m4a
    anweisung_02.m4a
    ...
```

Place source audio files (m4a) in the `ORIGINAL/` folder. On plug, they are
automatically converted to 8 kHz mono 16-bit WAV in the stick root. Only
re-converts files whose source is newer than the existing WAV. Removes WAVs
whose source m4a no longer exists.

### Supported source format

- M4A (AAC) files in `ORIGINAL/`
- Any filename; spaces are fine
- Conversion requires `ffmpeg` on the Pi

### Manual conversion (on any computer with ffmpeg)

```bash
./deploy/convert-audio.sh /path/to/mounted/stick
```

### If no stick is plugged in

The system plays a German fallback message ("Der USB Stick mit den Audio Daten fehlt.")
stored on the SD card at `/var/lib/asterisk/sounds/fluxus/no_audio_stick.wav`.

## Setup documentation

- [plan-fritzbox.md](plan-fritzbox.md) - FritzBox 7270 configuration
- [plan-raspberry-pi.md](plan-raspberry-pi.md) - Raspberry Pi OS setup, systemd services, USB stick handling
- [plan-asterisk.md](plan-asterisk.md) - Asterisk SIP/dialplan configuration, AMI setup

## Deploy files

All files to deploy to the Pi live in `deploy/`:

| File | Deploys to | Purpose |
|---|---|---|
| `fluxus-trigger.py` | `/usr/local/bin/fluxus-trigger.py` | Main trigger script (shuffled playback via AMI) |
| `fluxus-trigger.service` | `/etc/systemd/system/fluxus-trigger.service` | systemd unit for the trigger |
| `fluxus-trigger.env` | `/etc/fluxus-trigger.env` | AMI credentials and config |
| `fluxus-mount.sh` | `/usr/local/bin/fluxus-mount.sh` | Mount/unmount helper called by udev |
| `convert-audio.sh` | `/usr/local/bin/convert-audio.sh` | M4A to WAV conversion |
| `99-fluxus-audio.rules` | `/etc/udev/rules.d/99-fluxus-audio.rules` | udev rule for stick hot-plug |
