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
    return c.events

def check_events():
    events = get_events()
    now = datetime.now(timezone.utc)

    for e in events:
        event_time = e.begin.datetime

        # если timezone отсутствует — добавляем UTC
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        diff = (event_time - now).total_seconds()

        if 0 < diff <= 300:
            bot.send_message(
                CHAT_ID,
                f"⏰ Через 5 минут встреча:\n{e.name}\n{event_time:%H:%M}"
            )

check_events()
