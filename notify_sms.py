#!/usr/bin/env python3

import subprocess
import re
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
if not PHONE_NUMBER:
    raise Exception("PHONE_NUMBER not set in .env")

# Rate limiting
LAST_SENT_TIME = 0
MIN_INTERVAL = 10  # seconds

def send_sms(message):
    GAMMU_CONFIG = "/home/karthikey/gammu.config"
    global LAST_SENT_TIME
    now = time.time()
    if now - LAST_SENT_TIME < MIN_INTERVAL:
        print("[DEBUG] Skipping SMS due to rate limit.")
        return
    LAST_SENT_TIME = now

    try:
        short_message = message[:160].replace('\n', ' ')
        result = subprocess.run(
            ["gammu", "-c", GAMMU_CONFIG, "sendsms", "TEXT", PHONE_NUMBER],
            input=short_message.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print("[DEBUG] SMS sent. stdout:", result.stdout.decode())
        if result.stderr:
            print("[DEBUG] stderr:", result.stderr.decode())
    except subprocess.CalledProcessError as e:
        print("[ERROR] Failed to send SMS.")
        print(e.stderr.decode())
        print(e.stdout.decode())

def monitor_notifications():
    print("[DEBUG] Starting dbus-monitor listener...")
    proc = subprocess.Popen(
        ["dbus-monitor", "interface='org.freedesktop.Notifications'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    collecting = False
    strings = []
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("method call") and "org.freedesktop.Notifications" in line:
            collecting = True
            strings = []
            continue
        if collecting and line.startswith('string "'):
            value = re.sub(r'^string "(.*)"$', r"\1", line)
            strings.append(value)
            if len(strings) == 3:
                app_name, summary, body = strings
                # Gmail-specific handling
                if app_name.lower() == "google chrome" and "mail.google.com" in body:
                    sender, subject = parse_gmail_notification(body)
                    message = f"Email from {sender}: {subject}"
                    send_sms(message)
                else:
                    # Generic handling for other notifications
                    if app_name.lower() == "notify-send":
                        app_name = ""
                    parts = []
                    if app_name:
                        parts.append(f"[{app_name}]")
                    if summary:
                        parts.append(summary)
                    if body:
                        parts.append(body)
                    if parts:
                        message = ": ".join(parts) if len(parts) > 1 else parts[0]
                        send_sms(message)
                collecting = False

def parse_gmail_notification(body):
    """
    Extracts the sender's name and subject from the Gmail notification body.
    """
    lines = body.split("\n")
    sender = lines[0].strip() if len(lines) > 0 else "Unknown Sender"
    subject = lines[1].strip() if len(lines) > 1 else "No Subject"
    return sender, subject

if __name__ == "__main__":
    monitor_notifications()
