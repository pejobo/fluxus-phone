#!/bin/bash
# Deploy to: /usr/local/bin/fluxus-mount.sh
# Called by udev on stick plug/unplug

case "$1" in
    mount)
        /usr/bin/systemd-run --no-block /usr/local/bin/fluxus-mount.sh do-mount "$2"
        ;;
    do-mount)
        umount -l /mnt/audio 2>/dev/null
        mount -t vfat -o umask=022 "$2" /mnt/audio
        /usr/local/bin/convert-audio.sh /mnt/audio 2>/dev/null
        ;;
    umount)
        /usr/bin/systemd-run --no-block /bin/umount -l /mnt/audio
        ;;
esac
