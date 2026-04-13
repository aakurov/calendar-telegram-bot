import os
import requests
from datetime import datetime, timezone
import telegram

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

bot = telegram.Bot(token=TOKEN)


def parse_events():
    r = requests.get(ICS_URL)
    text = r.text

    events = []

    lines = text.splitlines()

    summary = None
    dtstart = None

    for line in lines:

        if line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()

        if line.startswith("DTSTART"):
            dtstart = line.split(":")[1].strip()

        if line.startswith("END:VEVENT"):
            if summary and dtstart:
                events.append((summary, dtstart))

            summary = None
            dtstart = None

    return events


def parse_time(dt):
    try:
        return datetime.strptime(dt, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    except:
        return None


def check_events():

    now = datetime.now(timezone.utc)

    events = parse_events()

    text = "🔎 Проверка календаря\n\n"

    for name, time_raw in events:

        event_time = parse_time(time_raw)

        if not event_time:
            continue

        diff = (event_time - now).total_seconds() / 60

        text += f"{event_time.strftime('%H:%M')} — {name} ({int(diff)} мин)\n"

        if 0 < diff <= 10:

            bot.send_message(
                CHAT_ID,
                f"⏰ Скоро встреча\n{name}\n{event_time.strftime('%H:%M')}"
            )

    bot.send_message(CHAT_ID, text)


check_events()
