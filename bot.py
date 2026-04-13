import os
import requests
from datetime import datetime, timezone

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

r = requests.get(ICS_URL)

lines = r.text.splitlines()

events = []

summary = None
dtstart = None

for line in lines:

    if line.startswith("SUMMARY:"):
        summary = line.replace("SUMMARY:", "").strip()

    if "DTSTART" in line:
        dtstart = line.split(":")[1].strip()

    if line.startswith("END:VEVENT"):
        if summary and dtstart:
            events.append((summary, dtstart))

        summary = None
        dtstart = None


msg = "📅 Найденные события:\n\n"

for name, t in events[:10]:
    msg += f"{name} | {t}\n"

send(msg)
