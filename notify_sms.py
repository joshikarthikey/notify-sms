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
    global LAST_SENT_TIME
    now = time.time()
    if now - LAST_SENT_TIME < MIN_INTERVAL:
        print("[DEBUG] Skipping SMS due to rate limit.")
        return
    LAST_SENT_TIME = now

    try:
        short_message = message[:160].replace('\n', ' ')
        print(f"[DEBUG] Sending SMS: {short_message}")
        result = subprocess.run(
            ["gammu", "sendsms", "TEXT", PHONE_NUMBER],
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
        print("[DEBUG] Raw line:", line)

        # Detect the start of a notification
        if line.startswith("method call") and "org.freedesktop.Notifications" in line and "Notify" in line:
            collecting = True
            strings = []
            linenum = 0
            continue

        # Collect strings when in the "collecting" state
        if collecting:
            if line.startswith('string "'):
                value = re.sub(r'^string "(.*)"$', r"\1", line)
                strings.append(value)
            elif strings[0] == "Google Chrome" and linenum == 6:
                strings.append(line.strip().replace('"', ''))
            linenum += 1
        

        # Process the notification when we have enough data
        if collecting and len(strings) >= 4:
            if strings[0] == "Google Chrome" and len(strings) < 5:
                continue
            elif strings[0] == "Google Chrome" and len(strings) == 5:
                _, _, sender, app_name, body = strings[:5]  # Extract the first five strings
                app_name = app_name.replace('string "', '').replace('"', '')
                print(f"[DEBUG] Extracted Notification - App: {app_name}, Sender: {sender}, Body: {body}")
            else:
                app_name, _, sender, body = strings[:4]  # Extract the first four strings
                print(f"[DEBUG] Extracted Notification - App: {app_name}, Summary: {sender}, Body: {body}")

            # Combine summary and body if summary is empty
            if not sender and body:
                sender, body = body, ""

            # Only send SMS if the notification contains meaningful data
            if app_name and (sender or body):  # Allow empty body if summary is present
                if strings[0] == "Google Chrome":
                    message = f"Hey man,{sender} sent you a message via {app_name}: {body}"
                else:
                    message_parts = []
                    if app_name:
                        message_parts.append(f"[{app_name}]")
                    if sender:
                        message_parts.append(sender)
                    if body:
                        message_parts.append(body)
                    message = ": ".join(message_parts)
                send_sms(message)
            else:
                print("[DEBUG] Skipping incomplete or irrelevant notification.")

            # Reset state for the next notification
            collecting = False
            strings = []

if __name__ == "__main__":
    monitor_notifications()
