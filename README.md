
# Desktop Notification to SMS Gateway on Fedora Linux

This project listens for desktop notifications (e.g., Gmail, WhatsApp Web, Instagram) on a Fedora desktop and forwards them as SMS using a USB GSM modem and [Gammu](https://wammu.eu/gammu/). It’s designed to run autonomously in the background and persist through lid close and modem replugging.

---

## Features

-  Captures desktop notifications via `dbus-monitor`
-  Parses app name, sender, and message content
-  Sends SMS alerts using [Gammu](https://wammu.eu/gammu/)
-  Runs persistently via user-level `systemd` service
-  Survives lid-close by overriding suspend behavior
-  Handles modem disconnects using udev symlink
-  Autosuspend workaround for reliable modem operation

---

## Prerequisites

- **Fedora Linux**
- **USB GSM modem** supported by Gammu (e.g. Huawei, ZTE, etc.)
- Python 3.8+
- Packages: `gammu`, `gammu-smsd`, `dbus`, `python3-dbus`, `dbus-tools`

### Install dependencies:

```bash
sudo dnf install python3-dbus gammu gammu-smsd dbus-tools
```

---

## Folder Structure

```
notify-sms/
├── notify_sms.py         # Python script that listens and sends SMS
├── gammu.config          # Gammu config with modem details
├── notify_sms.service    # systemd user service file
└── README.md
```

---

## 1. Python Script

Create `notify_sms.py` inside the project directory. It listens for notifications and invokes Gammu to send SMS messages.

Make it executable:

```bash
chmod +x notify_sms.py
```

---

## 2. Gammu Configuration

Create `gammu.config` in the project folder:

```ini
[gammu]
port = /dev/gsm_modem
connection = at
```

This config assumes your USB modem is symlinked to `/dev/gsm_modem`.

---

## 3. Create Udev Rule for Modem Symlink

Handle dynamic USB port assignments by symlinking modem to `/dev/gsm_modem`.

Create rule:

```bash
sudo nano /etc/udev/rules.d/99-gsm-modem.rules
```

Add:

```bash
SUBSYSTEM=="tty", ATTRS{bInterfaceNumber}=="02", ATTRS{driver}=="option", SYMLINK+="gsm_modem"
```

Reload udev:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## 4. systemd User Service

Create user service file:

```bash
mkdir -p ~/.config/systemd/user/
nano ~/.config/systemd/user/notify_sms.service
```

Paste:

```ini
[Unit]
Description=Send Desktop Notifications via SMS
After=default.target

[Service]
ExecStart=/usr/bin/python3 /home/karthikey/notify-sms/notify_sms.py
Restart=always

[Install]
WantedBy=default.target
```

Enable and start the service:

```bash
systemctl --user daemon-reload
systemctl --user enable notify_sms.service
systemctl --user start notify_sms.service
```

Monitor logs:

```bash
journalctl --user -u notify_sms.service -f
```

---

## 5. Prevent Suspend on Lid Close

Make Fedora ignore lid-close actions:

```bash
sudo mkdir -p /etc/systemd/logind.conf.d/
sudo nano /etc/systemd/logind.conf.d/logind.conf
```

Paste:

```ini
[Login]
HandleLidSwitch=ignore
HandleLidSwitchDocked=ignore
HandleLidSwitchExternalPower=ignore
LidSwitchIgnoreInhibited=no
```

Reload:

```bash
sudo systemctl restart systemd-logind
```

>  You may be logged out temporarily when this is applied.

---

##  6. Disable GNOME’s Power Overrides

Prevent GNOME from auto-suspending:

```bash
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
```

---

##  7. Fix USB Modem Autosuspend (if it disconnects after 1 SMS)

Check your modem ID:

```bash
lsusb
```

Then create a rule to keep it powered:

```bash
sudo nano /etc/udev/rules.d/99-usb-autosuspend.rules
```

Example rule:

```bash
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="XXXX", ATTR{idProduct}=="YYYY", TEST=="power/control", ATTR{power/control}="on"
```

Replace `XXXX` and `YYYY` with your modem’s Vendor/Product ID.

Reload:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## 8. Testing & Debugging

### Add your user to `dialout`:

```bash
sudo usermod -aG dialout $USER
newgrp dialout
```

### Test Gammu manually:

```bash
gammu -c gammu.config --identify
gammu -c gammu.config sendsms TEXT <your-phone-number> -text "Test SMS"
```

### Test notifications manually:

```bash
notify-send "Test App" "Test SMS body"
```

### Monitor the service:

```bash
journalctl --user -u notify_sms.service -f
```

---

##  Notes

- Tested on **Fedora Workstation** with GNOME.
- You can easily customize notification filters or message formats in the Python script.
- Can be adapted for other Linux distros with `systemd`, `gammu`, and `dbus`.
