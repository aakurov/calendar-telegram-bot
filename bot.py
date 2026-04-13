import requests
from ics import Calendar
from datetime import datetime, timezone
import os
import telegram

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

bot = telegram.Bot(token=TOKEN)

def get_events():
    r = requests.get(ICS_URL)
    c = Calendar(r.text)
    return list(c.events)

def normalize_time(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def send_today_schedule(events):
    now = datetime.now(timezone.utc)

    today_events = []

    for e in events:
        event_time = normalize_time(e.begin.datetime)

        if event_time.date() == now.date():
            today_events.append((event_time, e.name))

    if not today_events:
        return

    today_events.sort()

    text = "📅 Сегодняшние встречи:\n\n"

    for t, name in today_events:
        text += f"{t.strftime('%H:%M')} — {name}\n"

    bot.send_message(CHAT_ID, text)

def check_events():
    events = get_events()
    now = datetime.now(timezone.utc)

    # утренний план (примерно 9:00)
    if now.hour == 9 and now.minute < 2:
        send_today_schedule(events)

    for e in events:
        event_time = normalize_time(e.begin.datetime)

        diff = (event_time - now).total_seconds()

        if 240 < diff <= 300:
            bot.send_message(
                CHAT_ID,
                f"⏰ Через 5 минут встреча:\n{e.name}\n{event_time.strftime('%H:%M')}"
            )

check_events()
