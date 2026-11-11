import os, re, time, requests
from bs4 import BeautifulSoup

BOT_TOKEN = "9054593061:AAEH63VVrFlbWLNUTe6STuwGNqfwRsvmYNw"
CHAT_ID = "8308673733"
QUEUE = "6.2"
URL = "https://www.zoe.com.ua/outage/"
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_key.txt")  # рядом со скриптом, а не в папке запуска
EVERY = 300  # секунд между проверками


def parse(text, queue=QUEUE):
    """Свежий блок 'ОНОВЛЕНО ГПВ...' (он самый верхний) и строка нашей очереди."""
    h = re.search(r"ОНОВЛЕНО ГПВ НА[^\n]*", text)
    if not h:
        raise ValueError("заголовок графика не найден")
    m = re.search(rf"(?<![\d.]){re.escape(queue)}:\s*([^\n]+)", text[h.end():])
    if not m:
        raise ValueError(f"очередь {queue} не найдена")
    return " ".join(h.group(0).split()), m.group(1).strip()


def check():
    sample = ("ОНОВЛЕНО ГПВ НА 11 ЛИСТОПАДА (оновлено 12:56)\n5.2: 19:00 – 24:00\n"
              "6.1: 19:00 – 24:00\n6.2: 10:00 – 13:30, 19:00 – 24:00\n"
              "ОНОВЛЕНО ГПВ НА 11 ЛИСТОПАДА (оновлено 12:05)\n6.2: 10:00 – 15:00")
    assert parse(sample) == ("ОНОВЛЕНО ГПВ НА 11 ЛИСТОПАДА (оновлено 12:56)",
                             "10:00 – 13:30, 19:00 – 24:00")


def get_latest():
    r = requests.get(URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return parse(BeautifulSoup(r.text, "html.parser").get_text("\n"))


def notify(text):
    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text}, timeout=20)
    if not r.ok:
        raise RuntimeError(r.text)  # Telegram пишет причину ошибки в тексте ответа


if __name__ == "__main__":
    check()
    while True:
        try:
            header, line = get_latest()
            key = f"{header}|{line}"
            last = open(STATE, encoding="utf-8").read() if os.path.exists(STATE) else None
            if key != last:
                title = "✅ Скрипт запущен. Сейчас" if last is None else f"⚡ Новый график, очередь {QUEUE}"
                notify(f"{title}\n{header}\n{QUEUE}: {line}")
                # состояние пишем только после успешной отправки, иначе будет повтор
                open(STATE, "w", encoding="utf-8").write(key)
        except Exception as e:
            print("error:", e)
        time.sleep(EVERY)
