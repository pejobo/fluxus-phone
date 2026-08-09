# Deploy to: /usr/local/bin/fluxus-trigger.py
import os
import sys
import time
import random
import socket
from pathlib import Path

AUDIO_DIR = Path(os.environ.get("AUDIO_DIR", "/mnt/audio"))
FALLBACK_SOUND = os.environ.get("FALLBACK_SOUND", "/var/lib/asterisk/sounds/fluxus/no_audio_stick")
AMI_HOST = os.environ.get("AMI_HOST", "127.0.0.1")
AMI_PORT = int(os.environ.get("AMI_PORT", "5038"))
AMI_USER = os.environ["AMI_USER"]
AMI_SECRET = os.environ["AMI_SECRET"]
MIN_WAIT = int(os.environ.get("MIN_WAIT", "30"))
MAX_WAIT = int(os.environ.get("MAX_WAIT", "60"))

def ami_originate(sound_file):
    action = (
        f"Action: Originate\r\n"
        f"Channel: PJSIP/**1@fritzbox\r\n"
        f"Context: fluxus\r\n"
        f"Exten: _X.\r\n"
        f"Priority: 1\r\n"
        f"Variable: SOUND={sound_file}\r\n"
        f"Async: true\r\n"
        f"\r\n"
    )
    with socket.create_connection((AMI_HOST, AMI_PORT), timeout=5) as s:
        s.recv(1024)  # banner
        s.sendall(f"Action: Login\r\nUsername: {AMI_USER}\r\nSecret: {AMI_SECRET}\r\n\r\n".encode())
        s.recv(1024)
        s.sendall(action.encode())
        s.recv(1024)

def scan_audio_files():
    return [str(AUDIO_DIR / f.stem) for f in AUDIO_DIR.glob("*.wav")]

playlist = []

while True:
    try:
        if not playlist:
            playlist = scan_audio_files()
            random.shuffle(playlist)
        sound = playlist.pop() if playlist else FALLBACK_SOUND
        if not Path(sound + ".wav").exists() and sound != FALLBACK_SOUND:
            continue
        ami_originate(sound)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
    wait = random.uniform(MIN_WAIT, MAX_WAIT)
    time.sleep(wait)
