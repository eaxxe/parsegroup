import asyncio
import datetime
import os
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import F

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

GROUPS = {
    "Т-291": 56,
    "Т-517": 48
}

BASE_URL = "https://kbp.by/rasp/timetable/view_beta_kbp/?cat=group&id="


def get_weekday_column():
    weekday = datetime.datetime.now().weekday() + 1  # Пн=1
    return weekday + 1  # +1 потому что первый столбец номер пары


def parse_group(group_id, column_index):
    url = BASE_URL + str(group_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
        return ["-"] * 10  # если таблицы нет, возвращаем пустые строки

    rows = table.find_all("tr")
    results = []

    for row in rows[5:15]:  # строки 6-15
        cols = row.find_all("td")
        if len(cols) <= column_index:
            results.append("-")
            continue

        cell = cols[column_index]
        link = cell.find("a")
        if link and link.text.strip():
            results.append(link.text.strip())
        else:
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


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())