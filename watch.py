import os, re, signal, requests
from bs4 import BeautifulSoup

QUEUE = "6.2"
URL = "https://www.zoe.com.ua/outage/"
STATE = "last_key.txt"  # лежит в репозитории, workflow коммитит его при изменении


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
    r = requests.get(URL, timeout=(10, 20), headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    print("сайт ответил:", r.status_code, len(r.text), "байт")
    return parse(BeautifulSoup(r.text, "html.parser").get_text("\n"))


def notify(text):
    r = requests.post(f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/sendMessage",
                      data={"chat_id": os.environ["CHAT_ID"], "text": text}, timeout=20)
    if not r.ok:
        raise RuntimeError(r.text)


def _timeout(*_):
    raise TimeoutError("сайт слишком долго отвечает")


if __name__ == "__main__":
    check()
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(90)  # общий предел на весь запуск: requests сам не ограничивает долгую "капельную" загрузку
    header, line = get_latest()
    key = f"{header}|{line}"
    last = open(STATE, encoding="utf-8").read() if os.path.exists(STATE) else None
    if key != last:
        title = "✅ Скрипт запущен. Сейчас" if last is None else f"⚡ Новый график, очередь {QUEUE}"
        notify(f"{title}\n{header}\n{QUEUE}: {line}")
        # пишем только после успешной отправки, иначе при сбое будет повтор
        open(STATE, "w", encoding="utf-8").write(key)

