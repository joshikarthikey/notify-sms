# Desktop Notification to SMS Gateway on Fedora Linux

This project listens for desktop notifications (e.g., Gmail, WhatsApp Web, Instagram) on a Fedora desktop and forwards them via SMS using a USB GSM modem and Gammu.

## Features

- Listens to desktop notifications using `dbus-monitor`.
- Parses app name, sender, and message content.
- Sends SMS alerts using Gammu.
- Runs persistently as a user-level `systemd` service.
- Survives lid close by disabling suspend behavior.
- Handles modem disconnection with udev symlink.

---

## Prerequisites

- **Fedora Linux**
- **USB GSM modem** supported by Gammu
- Python 3.8+
- `gammu`, `gammu-smsd`
- D-Bus tools: `dbus`, `dbus-python`

### Install dependencies:

```bash
sudo dnf install python3-dbus gammu gammu-smsd dbus-tools
```

---

## Folder Structure

```
notify-sms/
├── notify_sms.py         # Python script that listens and sends SMS
├── gammu.config          # Gammu config with port and connection info
├── notify_sms.service    # systemd user service file
└── README.md
```

---

## 1. Python Script

Create `notify_sms.py` inside the project directory.

It listens for desktop notifications and uses Gammu to send them as SMS.

Make sure the script is executable:

```bash
chmod +x notify_sms.py
```

---

## 2. Gammu Configuration

Create a config file named `gammu.config` in the project directory:

```ini
[gammu]
port = /dev/gsm_modem
connection = at
```

Ensure the GSM modem is symlinked to `/dev/gsm_modem` using udev (see below).

---

## 3. Create Udev Rule

To handle dynamic USB port assignment:

```bash
sudo nano /etc/udev/rules.d/99-gsm-modem.rules
```

Paste:

```bash
SUBSYSTEM=="tty", ATTRS{bInterfaceNumber}=="02", ATTRS{driver}=="option", SYMLINK+="gsm_modem"
```

Reload udev:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## 4. Create systemd User Service

Save the following as `~/.config/systemd/user/notify_sms.service`:

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

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable notify_sms.service
systemctl --user start notify_sms.service
```

Check status:

```bash
systemctl --user status notify_sms.service
journalctl --user -u notify_sms.service -f
```

---

## 5. Prevent Suspend on Lid Close

Create config:

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

Reload login manager:

```bash
sudo systemctl restart systemd-logind
```

> ⚠️ This may cause logout — safe to apply and log in again.

---

## 6. GSettings (GNOME Power Management)

Make sure GNOME doesn't override your lid settings:

```bash
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
```

---

## Notes

- You may need to add your user to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
newgrp dialout
```

- If Gammu fails to detect the modem, replug it and check `/dev/gsm_modem` exists.
- You can test Gammu manually:

```bash
gammu -c gammu.config --identify
gammu -c gammu.config sendsms TEXT <your-phone-number> -text "Test SMS"
```
