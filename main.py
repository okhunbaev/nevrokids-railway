from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import os
from datetime import datetime
from aiohttp import web
from threading import Thread

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

pending_reply_to = {}
user_limits = {}
MAX_MESSAGES_PER_DAY = 3

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.reply(
        "Здравствуйте! Напишите полностью сформулированный вопрос. "
        f"Вы можете отправить не более {MAX_MESSAGES_PER_DAY} сообщений в сутки.\n\n"
        "Assalomu alaykum! Savolingizni to‘liq yozing. "
        f"Kuniga {MAX_MESSAGES_PER_DAY} ta xabar yuborishingiz mumkin."
    )

@dp.message_handler(lambda message: message.from_user.id != ADMIN_ID)
async def handle_user_message(message: types.Message):
    user_id = message.from_user.id
    today = datetime.now().strftime('%Y-%m-%d')

    if user_id not in user_limits or user_limits[user_id]['date'] != today:
        user_limits[user_id] = {"count": 0, "date": today}

    if user_limits[user_id]['count'] >= MAX_MESSAGES_PER_DAY:
        await message.reply(
            "Вы уже отправили 3 сообщения сегодня. Пожалуйста, подождите до завтра.\n\n"
            "Siz bugun 3 ta xabar yubordingiz. Iltimos, ertagacha kuting."
        )
        return

    user_limits[user_id]['count'] += 1

    username = message.from_user.username or f"ID: {user_id}"
    text = message.text

    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Ответить", callback_data=f"reply:{user_id}")
    )
    await bot.send_message(
        ADMIN_ID,
        f"Новое обращение от @{username} (ID: {user_id}):\n{text}",
        reply_markup=markup
    )
    await message.reply(
        "Ваш вопрос передан врачу. Ожидайте ответ.\n\n"
        "Savolingiz shifokorga yuborildi. Javobni kuting."
    )

@dp.callback_query_handler(lambda c: c.data.startswith("reply:"))
async def reply_callback(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split(":")[1])
    pending_reply_to[ADMIN_ID] = user_id
    await bot.send_message(ADMIN_ID, f"Напишите ответ — он будет отправлен пользователю ID {user_id}.\n\nJavob yozing — foydalanuvchiga yuboriladi.")
    await callback_query.answer("Ожидаю ваш ответ...")

@dp.message_handler(lambda message: message.from_user.id == ADMIN_ID)
async def admin_response(message: types.Message):
    if ADMIN_ID in pending_reply_to:
        user_id = pending_reply_to.pop(ADMIN_ID)
        await bot.send_message(user_id, f"Ответ от врача:\n{message.text}\n\nShifokordan javob:\n{message.text}")
        await message.reply("Ответ отправлен пользователю.\n\nJavob yuborildi.")
    else:
        await message.reply("Сначала нажмите кнопку 'Ответить' под сообщением пользователя.\n\nAvval 'Javob berish' tugmasini bosing.")

# Веб-сервер для UptimeRobot
async def handle(request):
    return web.Response(text="Bot is alive")

def run_web():
    app = web.Application()
    app.router.add_get("/", handle)
    web.run_app(app, port=PORT)

if __name__ == '__main__':
    Thread(target=run_web).start()
    executor.start_polling(dp, skip_updates=True)
