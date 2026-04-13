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
        diff = (e.begin.datetime - now).total_seconds()

        if 0 < diff <= 300:
            bot.send_message(
                CHAT_ID,
                f"⏰ Через 5 минут встреча:\n{e.name}\n{e.begin:%H:%M}"
            )

check_events()
