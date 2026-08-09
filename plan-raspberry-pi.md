# Raspberry Pi Setup Plan

## Goal
Raspberry Pi OS Lite (64-bit) running on a Pi 3B, booting from SD card.
Auto-starts Asterisk and the fluxus trigger script on every power-up.
Accessible via SSH over the FritzBox WLAN. No monitor or keyboard required
after initial setup.

---

## Hardware needed for initial setup
- Raspberry Pi 3B
- microSD card (≥8 GB, class 10 or faster)
- Another computer to flash the image
- Monitor + USB keyboard — only for first boot

---

## Part 1 — Flash Raspberry Pi OS Lite to the SD card

### 1a — Download the image
```bash
# Raspberry Pi OS Lite (64-bit, bookworm)
# https://www.raspberrypi.com/software/operating-systems/
```
Or use the Raspberry Pi Imager for a guided flow.

### 1b — Write the image
```bash
# identify the SD card — triple-check, wrong device = data loss
lsblk

dd if=raspios-lite-arm64.img of=/dev/sdX bs=4M status=progress
sync
```
Replace `/dev/sdX` with your SD card device.

### 1c — Enable SSH before first boot (headless option)
Mount the boot partition and create an empty file:
```bash
mount /dev/sdX1 /mnt
touch /mnt/ssh
umount /mnt
```
This enables the SSH server on first boot so you can skip the monitor if the
Pi gets a DHCP address you can find.

---

## Part 2 — First boot and initial configuration

Insert the SD card into the Pi. Connect monitor and keyboard. Power on.

Default credentials (bookworm): follow the first-boot wizard to create a user.
If using an older image: user `pi`, password `raspberry`.

### 2a — Create the fluxus user (if not done in wizard)
```bash
sudo adduser fluxus
sudo usermod -aG sudo,audio fluxus
```

Log out and log back in as `fluxus`.

### 2b — Full system update
```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

### 2c — Set hostname
```bash
sudo hostnamectl set-hostname fluxus
```

Edit `/etc/hosts`:
```
127.0.0.1   localhost
::1         localhost
127.0.1.1   fluxus.localdomain fluxus
```

### 2d — Set locale and timezone
```bash
sudo raspi-config
```
Navigate to: **Localisation Options** → set locale (`en_US.UTF-8`) and
timezone (`Europe/Berlin`).

Or via command line:
```bash
sudo timedatectl set-timezone Europe/Berlin
```

### 2e — Lock the default pi user (if it exists)
```bash
sudo passwd -l pi
```

### 2f — Set up SSH key login (recommended)
From your laptop, copy your public key:
```bash
ssh-copy-id fluxus@192.168.178.42
```
Or manually append your public key to `/home/fluxus/.ssh/authorized_keys` on the Pi.

Once confirmed working, disable password auth in `/etc/ssh/sshd_config`:
```
PasswordAuthentication no
```
Restart SSH:
```bash
sudo systemctl restart sshd
```

---

## Part 3 — Install packages

```bash
sudo apt install -y espeak-ng python3 sox
```

| Package | Purpose |
|---|---|
| `espeak-ng` | offline TTS for pre-rendering instruction audio |
| `python3` | trigger script runtime |
| `sox` | WAV conversion / normalisation |

SSH is already enabled by default on Raspberry Pi OS.

### Build Asterisk from source

Asterisk is not packaged in Debian Trixie. Build it manually:

```bash
# build dependencies
sudo apt install -y build-essential libedit-dev uuid-dev libxml2-dev \
  libsqlite3-dev libjansson-dev libssl-dev

cd /usr/local/src
sudo wget https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-22-current.tar.gz
sudo tar xzf asterisk-22-current.tar.gz
cd asterisk-22.*/

# configure for a minimal SIP/audio build
sudo contrib/scripts/install_prereq install
./configure
make menuselect.makeopts
# in menuselect: ensure res_pjsip, app_playback, app_dial are selected
make menuselect
make -j$(nproc)
sudo make install
sudo make samples
sudo make config   # installs systemd unit
```

Create the asterisk user:
```bash
sudo useradd -r -s /usr/sbin/nologin asterisk
sudo chown -R asterisk:asterisk /var/lib/asterisk /var/spool/asterisk \
  /var/log/asterisk /var/run/asterisk /etc/asterisk
```

---

## Part 4 — Directory layout

```bash
# fallback audio (system card — always present)
sudo mkdir -p /var/lib/asterisk/sounds/fluxus
sudo chown asterisk:asterisk /var/lib/asterisk/sounds/fluxus

# mount point for the audio USB stick
sudo mkdir -p /mnt/audio
sudo chown asterisk:asterisk /mnt/audio
```

Instruction WAV files live on the **USB stick** mounted at `/mnt/audio/`
(see Part 6 below and plan-asterisk.md Step 5).

The fallback audio (`no_audio_stick.wav`) lives on the SD card at
`/var/lib/asterisk/sounds/fluxus/` so it is always available even when the
audio stick is absent.

Place the trigger script at:
```
/usr/local/bin/fluxus-trigger.py
```

---

## Part 5 — Auto-start on boot

Enable Asterisk and the trigger service (units defined in plan-asterisk.md):
```bash
sudo systemctl enable asterisk
sudo systemctl enable fluxus-trigger
```

Ensure Asterisk waits for the network before starting (needed so it can reach
fritz.box for SIP registration):

```bash
sudo systemctl edit asterisk
```
Add:
```ini
[Unit]
After=network-online.target
Wants=network-online.target
```

Enable the network-online target:
```bash
sudo systemctl enable systemd-networkd-wait-online.service
```

### Verify on reboot
```bash
sudo reboot
# after boot, from another device on the FritzBox WLAN:
ssh fluxus@fluxus
systemctl status asterisk
systemctl status fluxus-trigger
```

---

## Part 6 — Audio USB stick (hot-plug)

Instruction audio lives on a separate FAT32 USB stick so it can be swapped or
updated from any computer without touching the SD card.

### 6a — Format the audio stick (on your computer)
```bash
# identify the stick — double-check with lsblk
mkfs.vfat -F 32 -n FLUX-PHON /dev/sdX1
```
Label must be exactly `FLUX-PHON` — the udev rule matches on this.

Place WAV files in the root of the stick, e.g.:
```
instruction_01.wav
instruction_02.wav
...
```
Files must be 8 kHz mono (see plan-asterisk.md Step 5 for conversion).

### 6b — Create the udev rule for auto-mount / auto-unmount
File: `/etc/udev/rules.d/99-fluxus-audio.rules`

```
ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_LABEL}=="FLUX-PHON", \
  RUN+="/usr/bin/systemd-mount --no-block --automount=no \
  --options=uid=asterisk,gid=asterisk,umask=022 \
  $env{DEVNAME} /mnt/audio"

ACTION=="remove", SUBSYSTEM=="block", ENV{ID_FS_LABEL}=="FLUX-PHON", \
  RUN+="/usr/bin/systemd-umount /mnt/audio"
```

`systemd-mount` is safe to call from udev — it spawns a transient mount unit
without blocking the udev event queue.

Reload udev rules:
```bash
sudo udevadm control --reload-rules
```

### 6c — Test hot-plug
Plug in the audio stick. After a moment:
```bash
ls /mnt/audio/
# should show the WAV files
```

Unplug it:
```bash
ls /mnt/audio/
# should be empty (mount gone)
```

### 6d — Pre-render the fallback audio
This file must exist on the **SD card** so it plays even when the audio
stick is absent:

```bash
espeak-ng -v de -s 110 "Der USB Stick mit den Audio Daten fehlt." \
  -w /tmp/no_audio_stick_raw.wav

sox /tmp/no_audio_stick_raw.wav \
  -r 8000 -c 1 -e signed-integer -b 16 \
  /var/lib/asterisk/sounds/fluxus/no_audio_stick.wav
```

---

## Result
- Pi boots from SD card
- Starts Asterisk and the trigger script via systemd
- Reachable over SSH on the FritzBox WLAN at its assigned IP
- No monitor or keyboard required after initial setup
- Audio USB stick hot-plugs to `/mnt/audio/`; if absent the fallback message
  plays in German
