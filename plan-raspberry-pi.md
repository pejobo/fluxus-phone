# Raspberry Pi Setup Plan

## Goal
Arch Linux ARM running on a Pi 3B, booting entirely from a USB stick.
Auto-starts Asterisk and the fluxus trigger script on every power-up.
Accessible via SSH over the FritzBox WLAN. No monitor or keyboard required
after initial setup.

---

## Hardware needed for initial setup
- Raspberry Pi 3B
- USB stick (≥8 GB, preferably a fast one — class 10 / USB 3.x)
- A temporary microSD card (any size ≥2 GB) — needed once to burn the USB boot fuse
- Another computer (Linux preferred) to flash the images
- Monitor + USB keyboard — only for first boot

---

## Part 1 — Enable USB boot on the Pi 3B (one-time)

The Pi 3B cannot boot from USB out of the box. A one-time OTP fuse must be
programmed. This survives power-cuts and cannot be undone.

### 1a — Flash Raspberry Pi OS Lite to the microSD card
On your computer:
```bash
# download Raspberry Pi OS Lite (32-bit, bookworm)
# https://www.raspberrypi.com/software/operating-systems/

dd if=raspios-lite.img of=/dev/sdX bs=4M status=progress
sync
```
Replace `/dev/sdX` with your SD card device.

### 1b — Boot the Pi from the SD card
Insert the SD card, no USB stick yet. Connect monitor and keyboard. Boot.
Log in: user `pi`, password `raspberry` (or follow first-boot wizard).

### 1c — Program the USB boot OTP fuse
```bash
echo program_usb_boot_mode=1 | sudo tee -a /boot/config.txt
sudo reboot
```

After reboot, verify the fuse is set:
```bash
vcgencmd otp_dump | grep 17:
# must show: 17:3020000a
```

Power off. Remove the SD card. It is no longer needed.

---

## Part 2 — Install Arch Linux ARM on the USB stick

Do this on your computer, not on the Pi.

### 2a — Download the image
```bash
# Arch Linux ARM for Raspberry Pi 3 (AArch64)
wget https://os.archlinuxarm.org/os/ArchLinuxARM-rpi-aarch64-latest.tar.gz
wget https://os.archlinuxarm.org/os/ArchLinuxARM-rpi-aarch64-latest.tar.gz.sig
```
Verify the signature before continuing (key from archlinuxarm.org/about/downloads).

### 2b — Partition the USB stick
```bash
# identify the USB stick — triple-check, wrong device = data loss
lsblk

fdisk /dev/sdX   # replace sdX with your USB stick
```

Inside fdisk:
1. `o` — create new DOS partition table
2. `n` → primary → partition 1 → default start → `+256M` (boot partition)
3. `t` → `c` (set type to W95 FAT32 LBA)
4. `n` → primary → partition 2 → default start → default end (rest of disk)
5. `w` — write and exit

Format:
```bash
mkfs.vfat -F 32 /dev/sdX1
mkfs.ext4 /dev/sdX2
```

### 2c — Extract the Arch Linux ARM tarball
```bash
mkdir -p /mnt/boot /mnt/root
mount /dev/sdX1 /mnt/boot
mount /dev/sdX2 /mnt/root

bsdtar -xpf ArchLinuxARM-rpi-aarch64-latest.tar.gz -C /mnt/root
sync

mv /mnt/root/boot/* /mnt/boot/
```

### 2d — Fix fstab
```bash
# get the UUIDs
blkid /dev/sdX1   # note UUID for boot
blkid /dev/sdX2   # note UUID for root

nano /mnt/root/etc/fstab
```

Set fstab to:
```
UUID=<boot-uuid>   /boot   vfat   defaults   0 2
UUID=<root-uuid>   /       ext4   defaults   0 1
```

### 2e — Unmount
```bash
umount /mnt/boot /mnt/root
sync
```

---

## Part 3 — First boot and initial configuration

Insert the USB stick into the Pi. Connect monitor and keyboard. Power on.

Default credentials:
- User: `alarm` / password: `alarm`
- Root: `root` / password: `root`

Log in as root.

### 3a — Initialize pacman keyring
```bash
pacman-key --init
pacman-key --populate archlinuxarm
```

### 3b — Full system update
```bash
pacman -Syu
```
Reboot if the kernel was updated:
```bash
reboot
```

### 3c — Set hostname
```bash
echo fluxus > /etc/hostname
```

Add to `/etc/hosts`:
```
127.0.0.1   localhost
::1         localhost
127.0.1.1   fluxus.localdomain fluxus
```

### 3d — Set locale and timezone
```bash
# uncomment en_US.UTF-8 (or your locale) in /etc/locale.gen
nano /etc/locale.gen

locale-gen
echo LANG=en_US.UTF-8 > /etc/locale.conf

ln -sf /usr/share/zoneinfo/Europe/Berlin /etc/localtime
# adjust timezone to your region
```

---

## Part 4 — User account

### 4a — Create the fluxus user
```bash
useradd -m -G wheel,audio -s /bin/bash fluxus
passwd fluxus   # set a strong password
```

### 4b — Enable sudo for wheel group
```bash
pacman -S sudo
EDITOR=nano visudo
# uncomment: %wheel ALL=(ALL:ALL) ALL
```

### 4c — Lock the default accounts
```bash
passwd -l alarm
passwd -l root
```

### 4d — Set up SSH key login (recommended)
From your laptop, copy your public key:
```bash
ssh-copy-id fluxus@192.168.178.42
```
Or manually append your public key to `/home/fluxus/.ssh/authorized_keys` on the Pi.

Once confirmed working, disable password auth in `/etc/ssh/sshd_config`:
```
PasswordAuthentication no
```

---

## Part 5 — Install packages

```bash
pacman -S asterisk espeak-ng python sox openssh
```

| Package | Purpose |
|---|---|
| `asterisk` | SIP engine, dialplan, audio playback |
| `espeak-ng` | offline TTS for pre-rendering instruction audio |
| `python` | trigger script runtime |
| `sox` | WAV conversion / normalisation |
| `openssh` | SSH server for remote access |

Enable SSH:
```bash
systemctl enable sshd
systemctl start sshd
```

---

## Part 6 — Directory layout

```bash
# fallback audio (system stick — always present)
mkdir -p /var/lib/asterisk/sounds/fluxus
chown asterisk:asterisk /var/lib/asterisk/sounds/fluxus

# mount point for the audio USB stick
mkdir -p /mnt/audio
chown asterisk:asterisk /mnt/audio
```

Instruction WAV files live on the **second USB stick** mounted at `/mnt/audio/`
(see Part 8 below and plan-asterisk.md Step 5).

The fallback audio (`no_audio_stick.wav`) lives on the system stick at
`/var/lib/asterisk/sounds/fluxus/` so it is always available even when the
audio stick is absent.

Place the trigger script at:
```
/usr/local/bin/fluxus-trigger.py
```

---

## Part 7 — Auto-start on boot

Enable Asterisk and the trigger service (units defined in plan-asterisk.md):
```bash
systemctl enable asterisk
systemctl enable fluxus-trigger
```

Ensure Asterisk waits for the network before starting (needed so it can reach
fritz.box for SIP registration):

Edit `/usr/lib/systemd/system/asterisk.service`, add to `[Unit]`:
```ini
After=network-online.target
Wants=network-online.target
```

Enable the network-online target:
```bash
systemctl enable systemd-networkd-wait-online.service
```

### Verify on reboot
```bash
reboot
# after boot, from another device on the FritzBox WLAN:
ssh fluxus@192.168.178.42
systemctl status asterisk
systemctl status fluxus-trigger
```

---

## Part 8 — Audio USB stick (hot-plug)

Instruction audio lives on a separate FAT32 USB stick so it can be swapped or
updated from any computer without touching the system stick.

### 8a — Format the audio stick (on your computer)
```bash
# identify the stick — double-check with lsblk
mkfs.vfat -F 32 -n FLUXUS_AUDIO /dev/sdX1
```
Label must be exactly `FLUXUS_AUDIO` — the udev rule matches on this.

Place WAV files in the root of the stick, e.g.:
```
instruction_01.wav
instruction_02.wav
...
```
Files must be 8 kHz mono (see plan-asterisk.md Step 5 for conversion).

### 8b — Create the udev rule for auto-mount / auto-unmount
File: `/etc/udev/rules.d/99-fluxus-audio.rules`

```
ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_LABEL}=="FLUXUS_AUDIO", \
  RUN+="/usr/bin/systemd-mount --no-block --automount=no \
  --options=uid=asterisk,gid=asterisk,umask=022 \
  $env{DEVNAME} /mnt/audio"

ACTION=="remove", SUBSYSTEM=="block", ENV{ID_FS_LABEL}=="FLUXUS_AUDIO", \
  RUN+="/usr/bin/systemd-umount /mnt/audio"
```

`systemd-mount` is safe to call from udev — it spawns a transient mount unit
without blocking the udev event queue.

Reload udev rules:
```bash
udevadm control --reload-rules
```

### 8c — Test hot-plug
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

### 8d — Pre-render the fallback audio
This file must exist on the **system stick** so it plays even when the audio
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
- Pi boots from USB stick, no SD card needed
- Logs in automatically, starts Asterisk and the trigger script via systemd
- Reachable over SSH on the FritzBox WLAN at its assigned IP
- No monitor or keyboard required after this point
- Audio USB stick hot-plugs to `/mnt/audio/`; if absent the fallback message
  plays in German
