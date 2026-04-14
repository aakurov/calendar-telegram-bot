import os
import re
import json
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

MSK = ZoneInfo("Europe/Moscow")
STATE_FILE = "state.json"

# Напоминаем за LEAD_MINUTES минут до встречи.
# WINDOW_MINUTES — запас на разрыв между часовыми cron-джобами в GitHub
# Actions: каждая джоба крутит bot.py ~55 минут, после чего до старта
# следующей проходит 5+ минут (плюс типичная задержка cron-триггера GH).
# Без этого запаса событие, попадающее в «слепую зону» на границе часа
# (например, встреча в 10:02 — предыдущая джоба закончилась в 9:55,
# следующая стартовала в 10:03), не ловит метку «за 5 минут».
LEAD_MINUTES = 5
WINDOW_MINUTES = 5

URL_RE = re.compile(r"https?://[^\s<>\"']+")
# Что считаем ссылкой на видеовстречу (в порядке приоритета).
MEETING_HOST_PRIORITY = (
    "telemost.yandex",
    "telemost.360.yandex",
    "meet.google.com",
    "zoom.us",
    "teams.microsoft.com",
    "meet.jit.si",
    "webex.com",
)


def send(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": "true",
            },
            timeout=30,
        )
        return True
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"sent": [], "morning": ""}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def to_msk(dt):
    """Нормализуем date/datetime из ICS в tz-aware MSK."""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=MSK)
        return dt.astimezone(MSK)
    if isinstance(dt, date):
        return datetime(dt.year, dt.month, dt.day, tzinfo=MSK)
    return None


def _clean_ics_text(value):
    """ICS DESCRIPTION/LOCATION может приходить с экранированием \\n, \\, и т.п."""
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\\n", "\n").replace("\\N", "\n")
    s = s.replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
    return s


def extract_meeting_url(ev):
    """
    Ищем ссылку на видеовстречу в событии. Приоритет:
      1. URL, которые хостятся на известных видеосервисах (Telemost, Meet, Zoom...).
      2. Любой http(s) URL из LOCATION.
      3. Любой http(s) URL из URL / X-поля.
      4. Любой http(s) URL из DESCRIPTION.
    """
    candidates = []

    for field in ("LOCATION", "URL", "X-GOOGLE-CONFERENCE", "DESCRIPTION"):
        raw = ev.get(field)
        if raw is None:
            continue
        text = _clean_ics_text(raw)
        for url in URL_RE.findall(text):
            url = url.rstrip(".,);]>\"'")
            candidates.append((field, url))

    if not candidates:
        return None

    # 1. Известные хосты — по приоритету списка.
    for host in MEETING_HOST_PRIORITY:
        for _, url in candidates:
            if host in url.lower():
                return url

    # 2. Любой URL из LOCATION.
    for field, url in candidates:
        if field == "LOCATION":
            return url

    # 3. URL / X-поле.
    for field, url in candidates:
        if field in ("URL", "X-GOOGLE-CONFERENCE"):
            return url

    # 4. Иначе — первая ссылка из DESCRIPTION.
    return candidates[0][1]


def get_events(now):
    r = requests.get(ICS_URL, timeout=30)
    r.raise_for_status()
    cal = icalendar.Calendar.from_ical(r.text)

    window_start = now - timedelta(hours=1)
    window_end = now + timedelta(days=2)
    occurrences = recurring_ical_events.of(cal).between(window_start, window_end)

    events = []
    for ev in occurrences:
        summary = str(ev.get("SUMMARY") or "").strip()
        dtstart = ev.get("DTSTART")
        if not summary or dtstart is None:
            continue
        t = to_msk(dtstart.dt)
        if t is None:
            continue
        url = extract_meeting_url(ev)
        events.append((t, summary, url))
    return events


def main():
    state = load_state()
    now = datetime.now(MSK)

    try:
        events = get_events(now)
    except Exception as e:
        print(f"Failed to fetch/parse ICS: {e}")
        return

    events.sort(key=lambda e: e[0])
    today = now.date()

    # --- утренний план дня ---
    if state.get("morning") != str(today) and now.hour >= 9:
        today_events = [e for e in events if e[0].date() == today and e[0] >= now]
        if today_events:
            lines = ["📅 Сегодня:\n"]
            for t, name, url in today_events:
                line = f"{t.strftime('%H:%M')} — {name}"
                if url:
                    line += f"\n{url}"
                lines.append(line)
            if not send("\n".join(lines)):
                # не помечаем день как обработанный — попробуем в след. итерации
                save_state(state)
                return
        state["morning"] = str(today)

    # --- напоминания за ~LEAD_MINUTES минут ---
    horizon = (LEAD_MINUTES + WINDOW_MINUTES) * 60
    sent_ids = set(state.get("sent", []))

    for t, name, url in events:
        diff = (t - now).total_seconds()
        if 0 < diff <= horizon:
            event_id = f"{name}|{t.isoformat()}"
            if event_id in sent_ids:
                continue
            mins_left = max(1, int(round(diff / 60)))
            msg = f"⏰ Через ~{mins_left} мин\n{name}\n{t.strftime('%H:%M')}"
            if url:
                msg += f"\n{url}"
            if send(msg):
                sent_ids.add(event_id)

    # Чистим старые id, чтобы state.json не рос бесконечно
    cutoff = (now - timedelta(days=2)).isoformat()
    pruned = []
    for eid in sent_ids:
        parts = eid.rsplit("|", 1)
        if len(parts) == 2 and parts[1] >= cutoff:
            pruned.append(eid)
    state["sent"] = pruned

    save_state(state)


if __name__ == "__main__":
    main()
