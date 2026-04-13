import os
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

MSK = ZoneInfo("Europe/Moscow")

STATE_FILE = "state.json"


def send(text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"sent": [], "daily": ""}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def parse_time(raw):
    try:
        if "T" in raw:
            return datetime.strptime(raw[:15], "%Y%m%dT%H%M%S").replace(tzinfo=MSK)
        else:
            return datetime.strptime(raw[:8], "%Y%m%d").replace(tzinfo=MSK)
    except:
        return None


def get_events():

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

    return events


state = load_state()

events = get_events()

now = datetime.now(MSK)

future = []

for t, name in events:

    diff = (t - now).total_seconds()

    if diff > 0:
        future.append((t, name, diff))

future.sort()

# --- Утренний план дня ---

today = now.date()

if state["daily"] != str(today) and now.hour >= 9:

    today_events = []

    for t, name, _ in future:
        if t.date() == today:
            today_events.append((t, name))

    if today_events:

        msg = "📅 Сегодня:\n\n"

        for t, name in today_events:
            msg += f"{t.strftime('%H:%M')} — {name}\n"

        send(msg)

    state["daily"] = str(today)

# --- Напоминания о встречах ---

for t, name, diff in future:

    event_id = f"{name}-{t}"

    if 0 < diff <= 600 and event_id not in state["sent"]:

        send(
            f"⏰ Через несколько минут встреча\n{name}\n{t.strftime('%H:%M')}"
        )

        state["sent"].append(event_id)
# activate cron
save_state(state)
