import os
import requests
from datetime import datetime, timezone
import telegram

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

bot = telegram.Bot(token=TOKEN)


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
                events.append((summary, dtstart))

            summary = None
            dtstart = None

    return events


def parse_time(raw):

    try:
        return datetime.strptime(raw[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    except:
        return None


def check_events():

    now = datetime.now(timezone.utc)

    events = get_events()

    debug = "📅 События календаря:\n\n"

    for name, raw_time in events:

        event_time = parse_time(raw_time)

        if not event_time:
            continue

        diff = (event_time - now).total_seconds() / 60

        debug += f"{event_time.strftime('%H:%M')} — {name} ({int(diff)} мин)\n"

        if 0 < diff <= 10:

            bot.send_message(
                CHAT_ID,
                f"⏰ Через несколько минут встреча\n{name}\n{event_time.strftime('%H:%M')}"
            )

    bot.send_message(CHAT_ID, debug)


check_events()
