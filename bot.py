import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI


# ==============================
# SETTINGS
# ==============================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openrouter/free"
HISTORY_FILE = "chat_history.json"


# ==============================
# CHECK KEYS
# ==============================

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN topilmadi")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY topilmadi")


# ==============================
# SAMI AI
# ==============================

SYSTEM_PROMPT = """
Sen Sami AI nomli Telegram AI yordamchisan.

Seni Samat Tulkunov yaratgan.

Agar foydalanuvchi:
"Seni kim yaratgan?"
"Kim seni yaratgan?"
"Sami AI kimniki?"
"Yaratuvching kim?"

deb so'rasa, faqat:

"Samat Tulkunov."

deb javob ber.

Boshqa ortiqcha gap qo'shma.

Foydalanuvchi bilan do'stona va tabiiy suhbatlash.

O'zbekcha yozsa o'zbekcha javob ber.
Ruscha yozsa ruscha javob ber.
Qozoqcha yozsa qozoqcha javob ber.
Inglizcha yozsa inglizcha javob ber.

Oldingi suhbatlarni eslab, kontekst sifatida ishlat.
"""


# ==============================
# OPENROUTER
# ==============================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)


# ==============================
# TELEGRAM
# ==============================

bot = Bot(
    token=TELEGRAM_TOKEN
)

dp = Dispatcher()


# ==============================
# HISTORY
# ==============================

def load_history():

    if not os.path.exists(HISTORY_FILE):
        return {}

    try:
        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception:
        return {}


history_data = load_history()


def save_history():

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history_data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ==============================
# PREPARE HISTORY
# ==============================

def prepare_history(user_id):

    old_history = history_data.get(
        str(user_id),
        []
    )

    messages = []

    for item in old_history:

        role = item.get("role")
        text = item.get("text", "")

        if role == "model":
            role = "assistant"

        if role not in ["user", "assistant"]:
            continue

        if not text:
            continue

        messages.append({
            "role": role,
            "content": text
        })

    return messages


# ==============================
# ASK AI
# ==============================

async def ask_ai(user_id, user_text):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(
        prepare_history(user_id)
    )

    messages.append({
        "role": "user",
        "content": user_text
    })

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=MODEL,
        messages=messages
    )

    return response.choices[0].message.content


# ==============================
# START
# ==============================

@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = str(message.from_user.id)

    if user_id not in history_data:
        history_data[user_id] = []

    save_history()

    await message.answer(
        "🤖 Salom!\n\n"
        "Men Sami AI.\n"
        "Suhbatimizni eslab turaman 🧠\n\n"
        "/clear — xotirani tozalash\n"
        "/help — yordam"
    )


# ==============================
# CLEAR
# ==============================

@dp.message(Command("clear"))
async def clear(message: types.Message):

    user_id = str(message.from_user.id)

    history_data[user_id] = []

    save_history()

    await message.answer(
        "🗑 Xotira tozalandi!"
    )


# ==============================
# HELP
# ==============================

@dp.message(Command("help"))
async def help_command(message: types.Message):

    await message.answer(
        "🤖 Sami AI\n\n"
        "/start — boshlash\n"
        "/clear — xotirani tozalash\n"
        "/help — yordam"
    )


# ==============================
# CHAT
# ==============================

@dp.message()
async def chat_message(message: types.Message):

    if not message.text:
        return

    user_id = str(message.from_user.id)
    user_text = message.text

    try:

        await bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )

        answer = await ask_ai(
            user_id,
            user_text
        )

        if not answer:
            answer = "❌ AI javob bermadi."

        history_data.setdefault(
            user_id,
            []
        )

        history_data[user_id].append({
            "role": "user",
            "text": user_text
        })

        history_data[user_id].append({
            "role": "assistant",
            "text": answer
        })

        save_history()

        for i in range(
            0,
            len(answer),
            4096
        ):
            await message.answer(
                answer[i:i + 4096]
            )

    except Exception as e:

        logging.exception(
            "AI error"
        )

        if "429" in str(e):

            await message.answer(
                "⏳ Free AI limiti tugadi. "
                "Keyinroq yana urinib ko'ring."
            )

        else:

            await message.answer(
                "❌ Xatolik:\n\n"
                f"{e}"
            )


# ==============================
# RUN
# ==============================

async def main():

    logging.basicConfig(
        level=logging.INFO
    )

    print(
        "🤖 Sami AI 24/7 server uchun tayyor!"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
