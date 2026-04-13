import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

MSK = ZoneInfo("Europe/Moscow")

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

def parse_time(raw):
    try:
        if "T" in raw:
            return datetime.strptime(raw[:15], "%Y%m%dT%H%M%S").replace(tzinfo=MSK)
        else:
            return datetime.strptime(raw[:8], "%Y%m%d").replace(tzinfo=MSK)
    except:
        return None


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

            t = parse_time(dtstart)

            if t:
                events.append((t, summary))

        summary = None
        dtstart = None


now = datetime.now(MSK)

future = []

for t, name in events:

    diff = (t - now).total_seconds()

    if diff > 0:
        future.append((t, name, diff))


future.sort()

msg = "📅 Ближайшие события:\n\n"

for t, name, diff in future[:5]:

    minutes = int(diff / 60)

    msg += f"{t.strftime('%H:%M')} — {name} ({minutes} мин)\n"

    if 0 < diff <= 600:

        send(
            f"⏰ Через несколько минут встреча\n{name}\n{t.strftime('%H:%M')}"
        )


send(msg)
