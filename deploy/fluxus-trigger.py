import os
import time
import random
import socket
from pathlib import Path

AUDIO_DIR = Path(os.environ.get("AUDIO_DIR", "/mnt/audio"))
AMI_HOST = os.environ.get("AMI_HOST", "127.0.0.1")
AMI_PORT = int(os.environ.get("AMI_PORT", "5038"))
AMI_USER = os.environ["AMI_USER"]
AMI_SECRET = os.environ["AMI_SECRET"]
MIN_WAIT = int(os.environ.get("MIN_WAIT", "300"))
MAX_WAIT = int(os.environ.get("MAX_WAIT", "1800"))

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

def scan_instructions():
    return [f.stem for f in AUDIO_DIR.glob("*.wav")]

while True:
    wait = random.uniform(MIN_WAIT, MAX_WAIT)
    time.sleep(wait)
    instructions = scan_instructions()
    if not instructions:
        continue
    sound = random.choice(instructions)
    try:
        ami_originate(sound)
    except Exception as e:
        pass  # silent fail, try again next cycle
