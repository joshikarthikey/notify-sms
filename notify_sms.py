#!/usr/bin/env python3

import subprocess
import re
import time
import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
load_dotenv()
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
if not PHONE_NUMBER:
    raise Exception("PHONE_NUMBER not set in .env")

LAST_SENT_TIME = 0
MIN_INTERVAL = 10  # seconds


def stop_modemmanager():
    """Stops ModemManager using sudo (requires NOPASSWD rule)."""
    try:
        subprocess.run(
            ["sudo", "/bin/systemctl", "stop", "ModemManager"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("[DEBUG] ModemManager stopped.")
    except Exception as e:
        print("[ERROR] Failed to stop ModemManager:", e)


def wait_for_modem(path="/dev/gsm_modem", timeout=10):
    """Waits for /dev/gsm_modem to reappear after release/reset."""
    print(f"[DEBUG] Waiting for modem {path} to become available...")
    for _ in range(timeout):
        if os.path.exists(path):
            print("[DEBUG] Modem is available.")
            return True
        time.sleep(1)
    print("[ERROR] Modem device did not reappear within timeout.")
    return False


def send_sms(message):
    global LAST_SENT_TIME
    now = time.time()
    if now - LAST_SENT_TIME < MIN_INTERVAL:
        print("[DEBUG] Skipping SMS due to rate limit.")
        return
    LAST_SENT_TIME = now

    short_message = message[:160].replace('\n', ' ')
    print(f"[DEBUG] Sending SMS: {short_message}")

    # Stop ModemManager and wait for modem
    stop_modemmanager()
    if not wait_for_modem():
        return

    try:
        command = ["gammu", "sendsms", "TEXT", PHONE_NUMBER]
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            stdout, stderr = proc.communicate(input=short_message.encode(), timeout=10)
            print("[DEBUG] SMS sent. stdout:", stdout.decode())
            if stderr:
                print("[DEBUG] stderr:", stderr.decode())
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            print("[ERROR] SMS send timed out and was killed.")
            print("[DEBUG] stdout after kill:", stdout.decode())
            print("[DEBUG] stderr after kill:", stderr.decode())
    except Exception as e:
        print("[ERROR] Exception during SMS send:", e)


def monitor_notifications():
    print("[DEBUG] Starting dbus-monitor listener...")
    proc = subprocess.Popen(
        ["dbus-monitor", "interface='org.freedesktop.Notifications'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    collecting = False
    strings = []

    for line in proc.stdout:
        line = line.strip()
        print("[DEBUG] Raw line:", line)

        if line.startswith("method call") and "org.freedesktop.Notifications" in line and "Notify" in line:
            collecting = True
            strings = []
            linenum = 0
            continue

        if collecting:
            if line.startswith('string "'):
                value = re.sub(r'^string "(.*)"$', r"\1", line)
                strings.append(value)
            elif strings[0] == "Google Chrome" and linenum == 6:
                strings.append(line.strip().replace('"', ''))
            linenum += 1

        if collecting and len(strings) >= 4:
            if strings[0] == "Google Chrome" and len(strings) < 5:
                continue
            elif strings[0] == "Google Chrome" and len(strings) == 5:
                _, _, sender, app_name, body = strings[:5]
                app_name = app_name.replace('string "', '').replace('"', '')
                print(f"[DEBUG] Extracted Notification - App: {app_name}, Sender: {sender}, Body: {body}")
            else:
                app_name, _, sender, body = strings[:4]
                print(f"[DEBUG] Extracted Notification - App: {app_name}, Summary: {sender}, Body: {body}")

            if not sender and body:
                sender, body = body, ""

            if app_name and (sender or body):
                if strings[0] == "Google Chrome":
                    message = f"Hey man, {sender} sent you a message via {app_name}: {body}"
                else:
                    parts = []
                    if app_name:
                        parts.append(f"[{app_name}]")
                    if sender:
                        parts.append(sender)
                    if body:
                        parts.append(body)
                    message = ": ".join(parts)
                send_sms(message)
            else:
                print("[DEBUG] Skipping incomplete or irrelevant notification.")

            collecting = False
            strings = []


if __name__ == "__main__":
    monitor_notifications()
