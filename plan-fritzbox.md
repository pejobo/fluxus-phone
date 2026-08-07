# FritzBox 7270 Configuration Plan

## Goal
Register the Raspberry Pi as an internal IP phone (SIP client) on the FritzBox.
The analog phone on FON1 should ring when the Pi originates a call to its internal number.

---

## Prerequisites
- FritzBox 7270 powered on, LAN cable to Pi
- Pi gets an IP via FritzBox DHCP (no static IP needed, fritz.box resolves)
- Web interface reachable at http://fritz.box or http://192.168.178.1

---

## Step 1 — Log into the web interface
- Open http://fritz.box in a browser
- Log in (default: no password on older firmware, or check label on device)
- Fritz!OS on the 7270 is likely 54.xx — UI is in German by default

---

## Step 2 — Check the analog phone's internal number
Navigate to: **Telefonie → Telefoniegeräte**

Find the entry for **FON 1** (the analog phone port). Note its internal number.
- Typical value: `**1` (dial `**1` to reach FON 1 from another internal device)
- Or it may show as a two-digit internal number like `50`

Write it down — this is what Asterisk will dial.

---

## Step 3 — Create an IP phone account for the Raspberry Pi
Navigate to: **Telefonie → Telefoniegeräte → Neues Gerät hinzufügen**

Select device type: **Telefon (mit und ohne Anrufbeantworter)**
Then select connection type: **LAN/WLAN (IP-Telefon)**

Fill in:
| Field | Value |
|---|---|
| Name | `raspberry-pi` (or any label) |
| Interne Rufnummer | assigned automatically, e.g. `620` — note this down |
| Kennwort | set a strong password — note this down for Asterisk |

Accept outgoing calls on: assign any available external line (or internal only is fine).
Accept incoming calls: not needed — the Pi only originates calls.

Save. The FritzBox will show the new device with its internal number.

---

## Step 4 — Note SIP registration details
After saving, collect these values for Asterisk's pjsip.conf:

| Parameter | Value |
|---|---|
| SIP registrar | `fritz.box` |
| SIP port | `5060` (default) |
| Username / auth ID | internal number assigned above, e.g. `620` |
| Password | the password set in Step 3 |
| Realm / domain | `fritz.box` |

---

## Step 5 — Verify DHCP lease on Pi
On the Pi:
```bash
ip addr show eth0
# note the assigned IP, e.g. 192.168.178.xx
ping fritz.box
```
The Pi must be able to reach fritz.box by hostname before Asterisk can register.

---

## Step 6 — Optional: disable call waiting on FON 1
If the analog phone is an old rotary or DTMF model with no display, call waiting tones
can be confusing. Disable it under:
**Telefonie → Telefoniegeräte → FON 1 → Bearbeiten → Anklopfen: Aus**

---

## Step 7 — Connect the FritzBox to the internet via LAN cable
This is useful for initial setup, firmware updates, or fetching time via NTP.
For the final plug-and-play deployment this step is optional — the installation
works fully offline.

The FritzBox 7270 is a DSL device by default. To use a plain LAN cable as the
internet uplink (e.g. plugged into a wall socket or an upstream router), you need
to switch it into **Kabelanschluss** mode. In this mode **LAN 1 becomes the WAN
port** and LAN 2–4 remain for your local devices.

### 7a — Change the internet connection type
Navigate to: **Einstellungen → Internet → Zugangsdaten**

Under **Internetanbieter / Anschlussart** select:
- **Kabel** (cable) — if the upstream provides DHCP (most common)
- Or **Anderer Internetanbieter → IP-Anschluss** on some firmware versions

Set the IP configuration to **DHCP** (the upstream router assigns an address).
If the upstream requires a static IP, fill in the fields manually.

Save and confirm the reboot if prompted.

### 7b — Plug in the cable
After saving:
1. Connect an Ethernet cable from your upstream router / wall socket to **LAN 1**
   on the FritzBox (it is now acting as the WAN port)
2. Connect your PC and the Pi to **LAN 2, 3, or 4**
3. Wait ~30 seconds for the FritzBox to get an IP from the upstream

### 7c — Verify internet connectivity
On the FritzBox web interface, **Übersicht** (overview) should show a green
internet status icon and an external IP address.

From the Pi:
```bash
ping -c 3 8.8.8.8
```

### 7d — Update firmware (recommended while online)
Navigate to: **Einstellungen → System → Firmware-Update → Jetzt suchen**

The 7270 reached end-of-life with Fritz!OS 54.05 (2014). No newer firmware
exists, but applying the latest available version for this model ensures the SIP
stack is at its most stable.

### 7e — Revert for offline deployment
When moving the installation to its final location without internet:
1. Either leave the cable unplugged — the FritzBox will keep working as a local
   network/PBX without an uplink
2. Or switch the connection type back to **DSL** / disconnect LAN 1 — internal
   SIP and DHCP are unaffected either way

---

## Step 8 — Enable WLAN for wireless remote access to the Pi
The FritzBox 7270 has dual-band WiFi (2.4 GHz + 5 GHz, 802.11n) and works as an
access point with no internet required. Any device that joins this WLAN lands in
the same 192.168.178.x subnet as the Pi, so you can SSH in directly.

### 8a — Configure the WLAN
Navigate to: **WLAN → Funknetz** (or **Einstellungen → WLAN → Funknetzwerk**)

| Field | Recommended value |
|---|---|
| WLAN aktiv | ✓ enabled |
| Netzwerkname (SSID) | something recognisable, e.g. `fluxus` |
| Frequenzband | 2.4 GHz (wider device compatibility) |

Then navigate to: **WLAN → Sicherheit**

| Field | Recommended value |
|---|---|
| Verschlüsselung | WPA2 (CCMP/AES) |
| WLAN-Netzwerkschlüssel | a passphrase you'll remember on-site |

Save. The FritzBox starts broadcasting the SSID immediately — no reboot needed.

### 8b — Enable SSH on the Raspberry Pi
On the Pi (do this during initial setup while you still have a keyboard/monitor):

```bash
pacman -S openssh
systemctl enable sshd
systemctl start sshd
```

### 8c — Find the Pi's IP address
Option A — from the FritzBox web interface:
Navigate to **Heimnetz → Netzwerk** and find `alarmpi` (Arch Linux ARM default
hostname) in the device list. Note the assigned IP, e.g. `192.168.178.42`.

Option B — from the Pi itself:
```bash
ip addr show eth0 | grep 'inet '
```

Option C — assign a static DHCP lease so the IP never changes:
In **Heimnetz → Netzwerk → [Pi entry] → Bearbeiten**, tick
**Diesem Netzwerkgerät immer dieselbe IPv4-Adresse zuweisen**.

### 8d — Connect and SSH
From any device on the `fluxus` WLAN:
```bash
ssh alarm@192.168.178.42   # default Arch Linux ARM user is 'alarm'
```

You now have full shell access to the Pi without a monitor or keyboard, purely
over the local WiFi that the FritzBox provides offline.

---

## Result
After this setup:
- The FritzBox knows the Pi as internal extension `620`
- The analog phone is reachable at `**1` (or its assigned number)
- Asterisk can register to fritz.box and dial `**1` to ring the analog phone
- Internet access available on LAN 1 during setup; unplugging it does not break
  the local phone system
- WLAN `fluxus` lets you SSH into the Pi from a laptop or phone on-site, no
  cables or monitor needed
