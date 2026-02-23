import asyncio
import datetime
import os
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import F
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

GROUPS = {
    "Т-291": 56,
    "Т-517": 48
}

BASE_URL = "https://kbp.by/rasp/timetable/view_beta_kbp/?cat=group&id="


def get_weekday_column():
    weekday = datetime.datetime.now().weekday()  # Пн=0
    return weekday  # первый столбец в таблице — Пн


def parse_group(group_id, column_index):
    url = BASE_URL + str(group_id)
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.RequestException:
        return ["-"] * 10

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    if not table:
        return ["-"] * 10

    rows = table.find_all("tr")
    results = []

    # строки с 6 по 15 (индексация с 0)
    for row in rows[5:15]:
        cols = row.find_all("td")
        if len(cols) <= column_index:
            results.append("-")
            continue

        cell = cols[column_index]

        # ищем все пары в ячейке
        pairs = cell.find_all("div", class_="pair")
        if not pairs:
            results.append("-")
            continue

        # берем последнюю добавленную, если есть
        selected_pair = None
        for p in pairs:
            if "added" in p.get("class", []):
                selected_pair = p
        if not selected_pair:
            selected_pair = pairs[-1]  # иначе берем последнюю

        # достаем кабинет
        place_div = selected_pair.find("div", class_="place")
        if place_div:
            link = place_div.find("a")
            if link and link.text.strip():
                results.append(link.text.strip())
                continue

        results.append("-")

    return results


def format_response(data1, data2):
    lines = ["Т-291 | Т-517"]
    for a, b in zip(data1, data2):
        lines.append(f"{a:<5} | {b}")
    return "\n".join(lines)


@dp.message(Command("start"))
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Получить расписание", callback_data="get_schedule")]
        ]
    )
    await message.answer("Нажми кнопку:", reply_markup=keyboard)


@dp.callback_query(F.data == "get_schedule")
async def schedule_handler(callback: CallbackQuery):
    await callback.answer()

    column_index = get_weekday_column()

    data_291 = parse_group(GROUPS["Т-291"], column_index)
    data_517 = parse_group(GROUPS["Т-517"], column_index)

    response_text = format_response(data_291, data_517)

    await callback.message.answer(f"<pre>{response_text}</pre>", parse_mode="HTML")


# --- Web сервер для Render ---
async def handle(request):
    return web.Response(text="Bot is running 🚀")


async def start_web_server():
    app = web.Application()
    app.add_routes([web.get("/", handle)])

    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server running on port {port}")


async def main():
    # Запускаем одновременно веб-сервер и polling бота
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )


if __name__ == "__main__":
    asyncio.run(main())