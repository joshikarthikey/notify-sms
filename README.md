
# SMS Notification Forwarder for Feature Phone Users 

## Purpose

This project is intended for users who are transitioning from smartphones to feature phones and want to **stay notified about important digital communications**. With this solution, every desktop notification (e.g., from Gmail, Outlook, WhatsApp Web, Instagram, Slack, etc.) will be **forwarded as an SMS** using a GSM modem connected to your Fedora system.

## Core Idea

Turn your Linux desktop into a smart SMS forwarder that captures D-Bus desktop notifications and relays them to your feature phone via `gammu`.

---

## ⚙ System Architecture

```
+------------------------+      +----------------------------+
| D-Bus Notification API | -->  |   Python Listener Script   |
+------------------------+      +----------------------------+
                                               |
                                               v
                                     +------------------+
                                     |  Gammu CLI + GSM |
                                     |    (SMS Sender)  |
                                     +------------------+
                                               |
                                               v
                                    +----------------------+
                                    |   Feature Phone SMS  |
                                    +----------------------+
```

---

## Prerequisites

### Hardware

- Linux machine (tested on Fedora)
- USB GSM Modem (like Huawei E303, SIM800L USB, etc.)
- SIM card with SMS service
- Feature phone

### Software

- Python 3
- `gammu` & `gammu-smsd`
- `dbus`, `gi`, and `dbus-monitor`
- `.env` file with:
  ```env
  PHONE_NUMBER=+911234567890
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
  ```

---

##  Installation & Setup

### 1. Install Dependencies

```bash
sudo dnf install python3 python3-pip gammu minicom
pip install python-dotenv
```

### 2. Configure Gammu

Create `gammu.config`:

```ini
[gammu]
port = /dev/ttyUSB0
connection = at
```

Test it:

```bash
gammu -c gammu.config --identify
```

You may need to stop ModemManager:

```bash
sudo systemctl stop ModemManager
```

### 3. Test SMS Sending

```bash
echo "Hello" | gammu -c gammu.config sendsms TEXT +911234567890
```

If this works, Gammu is configured properly.

---

## D-Bus Notification Capture

Instead of using unreliable Python D-Bus bindings, we now use `dbus-monitor`:

```bash
dbus-monitor "interface='org.freedesktop.Notifications'"
```

This ensures notifications are reliably intercepted regardless of lock screen state.

---

## Python Script

- Listens to `dbus-monitor` for incoming desktop notifications
- Sends SMS via `gammu` with a 10-second rate limit

Make it executable and run:

```bash
chmod +x notify_sms.py
./notify_sms.py
```

You should see:

```
[DEBUG] Starting dbus-monitor listener...
[DEBUG] SMS sent. stdout: ...
```

---

## Lock Screen Behavior

Fedora locks the screen on lid-close. Override this:

```bash
sudo nano /etc/systemd/logind.conf
```

Set:
```
HandleLidSwitch=ignore
```

Then:

```bash
sudo systemctl restart systemd-logind
```

---

## Pitfalls & Challenges

- **Modem Busy**: `ModemManager` may hijack `/dev/ttyUSB0`
- **Permissions**: Add yourself to `dialout` group: `sudo usermod -aG dialout $USER`
- **Lockscreen Filtering**: Resolved using `dbus-monitor` instead of D-Bus Python APIs
- **Gammu config fallback**: Always use `-c gammu.config` explicitly
- **Debugging**: Use `minicom` to test modem AT commands directly

---

## Notification Support

This tool forwards system notifications via SMS with special handling for different notification types:

### Enhanced Support
- **Google Chrome Web Apps**: Optimized handling for:
  - Gmail notifications
  - WhatsApp Web notifications
  - Other web-based messaging apps running in Chrome

### General Support
- **System-wide notifications**: Generic handling for all other desktop notifications with a fallback format of `[App Name]: Summary: Body`

The notification parser is designed to extract meaningful information regardless of the notification source, ensuring you stay informed even when away from your computer.

Note: Chrome web app notifications receive special formatting to provide clearer sender/message context in the SMS output.

---

## Current Issues

- Messages from all apps are sent, even unimportant ones
- No message history or deduplication
- Long SMS split is not implemented yet
- Gammu config must be explicitly used (`-c gammu.config`)

---

## Future Improvements

- Filter messages by importance or app
- Bundle as a Fedora `.rpm` package
- Support Windows `.exe` for cross-platform usage
- Logging and error notifications
- Email IMAP integration for Gmail/Outlook summaries

---

## Packaging Plan

### Fedora RPM

- Create `.spec` file
- Install script as service
- Add `.env`, `.service`, and `gammu.config` templates

### Windows `.exe`

- Use `pyinstaller` to convert script to executable
- May require virtual modem for testing or SMS gateway
