import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_polling
from datetime import datetime

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.getenv("PORT", 8080))

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
        InlineKeyboardButton("Ўзбекча", callback_data="lang:uz")
    )
    await message.answer("Выберите язык / Тилни танланг:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("lang:"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split(":")[1]
    user_lang[callback.from_user.id] = lang
    text = "Язык выбран ✅\n\nНапишите свой вопрос врачу." if lang == "ru" else "Тил танланди ✅\n\nСаволингизни шифокорга ёзинг."
    await callback.message.edit_text(text)

@dp.message_handler(lambda m: m.from_user.id != ADMIN_ID)
async def user_message(message: types.Message):
    uid = message.from_user.id
    lang = user_lang.get(uid, "ru")
    today = datetime.now().strftime('%Y-%m-%d')

    if uid not in user_limits or user_limits[uid]['date'] != today:
        user_limits[uid] = {"count": 0, "date": today}

    if user_limits[uid]['count'] >= MAX_MESSAGES_PER_DAY:
        msg = "Вы уже отправили 3 сообщения сегодня. Подождите до завтра." if lang == "ru" else "Сиз бугун 3 та хабар юбордингиз. Илтимос, эртага ёзинг."
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

    reply = "Ваш вопрос отправлен врачу. Ожидайте ответ." if lang == "ru" else "Саволингиз шифокорга юборилди. Жавобни кутинг."
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
        lang = user_lang.get(uid, "ru")
        response = "Ответ от врача:\n" if lang == "ru" else "Шифокордан жавоб:\n"
        await bot.send_message(uid, f"{response}{message.text}")
        await message.answer("Ответ отправлен." if lang == "ru" else "Жавоб юборилди.")
    else:
        await message.answer("Сначала нажмите кнопку 'Ответить'." if lang == "ru" else "Аввал 'Жавоб бериш' тугмасини босинг.")

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
