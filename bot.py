import os
import requests

TOKEN = os.environ["TG_TOKEN"]
CHAT_ID = os.environ["TG_CHAT"]
ICS_URL = os.environ["ICS_URL"]

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

r = requests.get(ICS_URL)

text = r.text[:2000]

data = {
    "chat_id": CHAT_ID,
    "text": "Первые строки календаря:\n\n" + text
}

requests.post(url, data=data)
