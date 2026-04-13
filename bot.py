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


def debug_events(events):
    now = datetime.now(timezone.utc)

    text = "🔎 Тест бота\n\nБлижайшие события:\n"

    found = False

    for e in events:
        event_time = normalize_time(e.begin.datetime)
        diff_minutes = int((event_time - now).total_seconds() / 60)

        if -60 < diff_minutes < 1440:
            found = True
            text += f"{event_time.strftime('%H:%M')} — {e.name} ({diff_minutes} мин)\n"

    if not found:
        text += "нет ближайших событий"

    bot.send_message(CHAT_ID, text)


def check_events():
    events = get_events()
    now = datetime.now(timezone.utc)

    for e in events:
        event_time = normalize_time(e.begin.datetime)

        diff = (event_time - now).total_seconds()

        if 0 < diff <= 600:
            bot.send_message(
                CHAT_ID,
                f"⏰ Скоро встреча:\n{e.name}\n{event_time.strftime('%H:%M')}"
            )


events = get_events()

# сообщение что бот запустился
bot.send_message(CHAT_ID, "✅ бот запустился")

# показать события
debug_events(events)

# проверить уведомления
check_events()
