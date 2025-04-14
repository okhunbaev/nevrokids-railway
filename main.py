import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_webhook
from datetime import datetime
from aiohttp import web

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 8080))

WEBHOOK_HOST = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}" if os.getenv("RENDER_EXTERNAL_HOSTNAME") else None
WEBHOOK_PATH = "/webhook"
WEBAPP_HOST = "0.0.0.0"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_lang = {}
user_limits = {}
pending_reply_to = {}
MAX_MESSAGES_PER_DAY = 3

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("Русский", callback_data="lang:ru"),
        InlineKeyboardButton("O‘zbek", callback_data="lang:uz")
    )
    await message.answer("Выберите язык / Tilni tanlang:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("lang:"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split(":")[1]
    user_lang[callback.from_user.id] = lang
    await callback.message.edit_text(
        "Язык выбран ✅" if lang == "ru" else "Til tanlandi ✅"
    )

@dp.message_handler(lambda m: m.from_user.id != ADMIN_ID)
async def user_message(message: types.Message):
    uid = message.from_user.id
    lang = user_lang.get(uid, "ru")
    today = datetime.now().strftime('%Y-%m-%d')

    if uid not in user_limits or user_limits[uid]['date'] != today:
        user_limits[uid] = {"count": 0, "date": today}

    if user_limits[uid]['count'] >= MAX_MESSAGES_PER_DAY:
        msg = "Вы уже отправили 3 сообщения сегодня. Подождите до завтра." if lang == "ru" else "Siz bugun 3 ta xabar yubordingiz. Ertaga yozing."
        return await message.answer(msg)

    user_limits[uid]['count'] += 1
    username = message.from_user.username or f"ID: {uid}"
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Ответить", callback_data=f"reply:{uid}")
    )

    await bot.send_message(
        ADMIN_ID,
        f"Новое сообщение от @{username} (ID: {uid}):\n{message.text}",
        reply_markup=markup
    )

    reply = "Ваш вопрос отправлен врачу. Ожидайте ответ." if lang == "ru" else "Savolingiz yuborildi. Javobni kuting."
    await message.reply(reply)

@dp.callback_query_handler(lambda c: c.data.startswith("reply:"))
async def reply_admin(callback: types.CallbackQuery):
    uid = int(callback.data.split(":")[1])
    pending_reply_to[ADMIN_ID] = uid
    await callback.message.answer(f"Напишите ответ пользователю ID {uid}.")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID)
async def admin_reply(message: types.Message):
    if ADMIN_ID in pending_reply_to:
        uid = pending_reply_to.pop(ADMIN_ID)
        await bot.send_message(uid, f"Ответ от врача:\n{message.text}")
        await message.answer("Ответ отправлен.")
    else:
        await message.answer("Сначала нажмите кнопку 'Ответить'.")

# Aiohttp для Render
async def health_check(request):
    return web.Response(text="Bot is alive")

async def on_startup(dp):
    if WEBHOOK_HOST:
        await bot.set_webhook(f"{WEBHOOK_HOST}{WEBHOOK_PATH}")

async def on_shutdown(dp):
    await bot.delete_webhook()

app = web.Application()
app.router.add_get("/", health_check)

# Запуск бота через webhook или polling
if __name__ == "__main__":
    if WEBHOOK_HOST:
        start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=PORT,
            web_app=app
        )
    else:
        import asyncio
        async def run():
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, WEBAPP_HOST, PORT)
            await site.start()
            await dp.start_polling()
        asyncio.run(run())
