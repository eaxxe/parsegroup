import asyncio
import datetime
import os
from playwright.async_api import async_playwright
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import F

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

GROUPS = {"Т-291": 56, "Т-517": 48}
BASE_URL = "https://kbp.by/rasp/timetable/view_beta_kbp/?cat=group&id="

def get_weekday_column():
    weekday = datetime.datetime.now().weekday() + 1  # Пн=1
    return weekday + 1  # первая колонка — номер пары

async def parse_group_playwright(group_id, column_index):
    url = BASE_URL + str(group_id)
    async with async_playwright() as p:
        # Запускаем браузер в headless-режиме с параметрами для Render
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = await browser.new_page()
        # Устанавливаем корректный User-Agent
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        await page.goto(url, wait_until="networkidle")
        # Ждём появления таблицы (до 15 секунд)
        await page.wait_for_selector('table', timeout=15000)
        # Извлекаем все строки таблицы
        rows = await page.query_selector_all('table tr')
        results = []
        # Пропускаем заголовки (первые две строки) и берём следующие 10 (пары 1-10)
        for i in range(2, 12):  # индексы 2..11 = 10 строк
            if i >= len(rows):
                results.append("-")
                continue
            cells = await rows[i].query_selector_all('td')
            if len(cells) <= column_index:
                results.append("-")
                continue
            cell = cells[column_index]
            # Ищем ссылку внутри ячейки
            link = await cell.query_selector('a')
            if link:
                text = await link.text_content()
                results.append(text.strip() if text else "-")
            else:
                results.append("-")
        await browser.close()
        return results

def format_response(data1, data2):
    lines = ["Т-291 | Т-517"]
    for a, b in zip(data1, data2):
        lines.append(f"{a:<30} | {b}")
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
    # Запускаем парсинг параллельно
    data_291, data_517 = await asyncio.gather(
        parse_group_playwright(GROUPS["Т-291"], column_index),
        parse_group_playwright(GROUPS["Т-517"], column_index)
    )
    response_text = format_response(data_291, data_517)
    await callback.message.answer(f"<pre>{response_text}</pre>", parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())