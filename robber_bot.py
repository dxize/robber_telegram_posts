import asyncio
import os
import tempfile
import shutil
from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import Router
from telethon.errors import FloodWaitError
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    DocumentAttributeVideo,
)

# Конфигурация
api_id = "25330009"  # Ваш API ID
api_hash = "5e96e4d16e421a3961b7caef5f0ccb96"  # Ваш API Hash
BOT_TOKEN = "7280058903:AAGJZkeoNsHjlwRACHAXTBTZppPSXLkl1lM"  # Токен вашего бота
session_name = "MyClientSession"  # Имя сессии для клиента

# ID вашего канала для публикации
target_channel_id = "@adkadkdc"  # Замените на ID вашего канала

# Список каналов для получения сообщений
source_channel_usernames = [
    "@WalkerAmongTheStars",
    "@why4ch",
    "@dvachannel",
    "@ru2ch",
    "@dfasdfasa",
]

# Инициализация бота и клиента
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Создание временного файла сессии
with tempfile.NamedTemporaryFile(
    delete=False, suffix=".session", prefix=session_name
) as temp_session:
    session_file = temp_session.name
    print(f"Используется временный файл сессии: {session_file}")

client = TelegramClient(session_file, api_id, api_hash)

# Словарь для хранения данных пользователей
user_data = {}

MAX_CAPTION_LENGTH = 1024  # Максимальная длина заголовка


async def send_message_with_retries(client, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await client.send_message(*args, **kwargs)
        except FloodWaitError as e:
            print(f"Flood wait error: {e}. Retrying in {e.seconds} seconds.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error sending message: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Delay before retrying


async def send_file_with_retries(client, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await client.send_file(*args, **kwargs)
        except FloodWaitError as e:
            print(f"Flood wait error: {e}. Retrying in {e.seconds} seconds.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error sending file: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Delay before retrying


async def send_video_note_as_circle(client, target_channel_id, file_path, caption=None):
    try:
        # Отправка видео как "кружочка" (video message)
        await client.send_file(
            target_channel_id,
            file_path,
            caption=caption,
            attributes=[
                DocumentAttributeVideo(duration=0, w=640, h=640, round_message=True)
            ],
            voice_note=False,
            video_note=True,
            supports_streaming=True,
        )
        print(f"Кружочек отправлен: {file_path}")
    except Exception as e:
        print(f"Ошибка при отправке кружочка: {e}")


async def download_and_send_as_circle(message, media):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        file_path = temp_file.name
        print(f"Загружаем медиа в: {file_path}")

        try:
            await client.download_media(media, file_path)
            if os.path.exists(file_path):
                await send_video_note_as_circle(
                    client,
                    target_channel_id,
                    file_path,
                    caption=message.raw_text[:MAX_CAPTION_LENGTH],
                )
            else:
                print(f"Файл {file_path} не существует, пропуск отправки.")
        except Exception as e:
            print(f"Ошибка при загрузке и отправке медиа: {e}")
        finally:
            try:
                temp_file.close()
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Удален временный файл: {file_path}")
            except Exception as e:
                print(f"Ошибка при удалении файла {file_path}: {e}")


async def download_media_and_send(message, media, text):
    if isinstance(media, MessageMediaPhoto):
        file_extension = ".jpg"
    elif isinstance(media, MessageMediaDocument):
        mime_type = media.document.mime_type
        if mime_type.startswith("video"):
            file_extension = ".mp4"
        elif mime_type.startswith("audio"):
            file_extension = ".ogg"
        else:
            file_extension = ".bin"
    else:
        file_extension = ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        file_path = temp_file.name
        print(f"Загружаем медиа в: {file_path}")

        try:
            # Загружаем медиафайл
            await client.download_media(media, file_path)

            # Проверяем, что файл существует перед отправкой
            if os.path.exists(file_path):
                # Обрезаем текст, чтобы он не превышал допустимую длину
                caption = text[:MAX_CAPTION_LENGTH]

                # Отправка медиафайла с текстом
                await send_file_with_retries(
                    client, target_channel_id, file_path, caption=caption
                )
                print(f"Медиа отправлено: {file_path}")
            else:
                print(f"Файл {file_path} не существует, пропуск отправки.")

        except Exception as e:
            print(f"Ошибка при загрузке и отправке медиа: {e}")

        finally:
            try:
                # Задержка для обеспечения завершения всех операций с файлом
                await asyncio.sleep(0.5)

                # Явное закрытие файла перед удалением
                temp_file.close()

                # Удаляем файл после завершения всех операций
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Удален временный файл: {file_path}")
            except Exception as e:
                print(f"Ошибка при удалении файла {file_path}: {e}")


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
                print("Connecting client...")
                await client.connect()

                if not await client.is_user_authorized():
                    print("Sending code request...")
                    sent_code = await client.send_code_request(phone_number)
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
            await client.sign_in(
                phone_number, phone_code, phone_code_hash=phone_code_hash
            )
            me = await client.get_me()
            await message.answer(
                f"Пользователь с номером {phone_number} успешно авторизован! Привет, {me.first_name}."
            )
            print("Client connected.")
            user_data.pop(user_id, None)
        except Exception as e:
            await message.answer(f"Ошибка авторизации: {e}")
            print("Client not authorized. Please authorize the client.")
    else:
        await message.answer("Используйте команду /start для начала.")


# Временное хранилище для сообщений из медиа-групп с меткой времени последнего сообщения
grouped_messages = defaultdict(
    lambda: {"messages": [], "timestamp": datetime.now(timezone.utc)}
)
media_group_tasks = {}

MEDIA_GROUP_TIMEOUT = timedelta(
    seconds=1
)  # Таймаут для сбора всех сообщений в медиа-группе

# Путь к временной папке
script_dir = os.path.dirname(os.path.abspath(__file__))
temp_dir = os.path.join(script_dir, "temp_media")

# Создаем временную папку для хранения медиафайлов
os.makedirs(temp_dir, exist_ok=True)


async def process_media_group(group_id):
    group_data = grouped_messages.get(group_id)
    if not group_data:
        return

    media_files = []
    captions = []

    for msg in group_data["messages"]:
        if msg.media:
            # Сохранение медиафайлов во временные файлы
            file_extension = ""
            if isinstance(msg.media, MessageMediaPhoto):
                file_extension = ".jpg"
            elif isinstance(msg.media, MessageMediaDocument):
                file_extension = (
                    os.path.splitext(msg.media.document.attributes[0].file_name)[1]
                    if msg.media.document.attributes
                    else ".bin"
                )

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=file_extension
            ) as temp_file:
                file_path = temp_file.name
                print(f"Загружаем медиа в: {file_path}")

                try:
                    await client.download_media(msg.media, file_path)
                    media_files.append(file_path)
                except Exception as e:
                    print(f"Ошибка при загрузке медиа: {e}")

        if msg.raw_text:
            captions.append(msg.raw_text)

    # Соединяем все тексты
    caption = "\n".join(captions)[:MAX_CAPTION_LENGTH]

    if media_files:
        try:
            # Отправляем все медиафайлы как одну медиа-группу с общим текстом
            await send_file_with_retries(
                client,
                target_channel_id,
                media_files,
                caption=caption,
                parse_mode="html",
            )
        except Exception as e:
            print(f"Ошибка при отправке медиа-группы: {e}")
        finally:
            # Удаляем все временные файлы
            for file_path in media_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Удален временный файл: {file_path}")
    else:
        # Если медиа-файлов нет, просто отправляем текст
        await send_message_with_retries(
            client,
            target_channel_id,
            caption,
            parse_mode="html",
        )

    del grouped_messages[group_id]


async def handle_media_group_timeout(group_id):
    await asyncio.sleep(MEDIA_GROUP_TIMEOUT.total_seconds())
    current_time = datetime.now(timezone.utc)
    if current_time - grouped_messages[group_id]["timestamp"] > MEDIA_GROUP_TIMEOUT:
        await process_media_group(group_id)


@client.on(events.NewMessage(chats=source_channel_usernames))
async def handler(event):
    message = event.message
    current_time = datetime.now(timezone.utc)

    # Проверяем, содержит ли сообщение ссылку
    contains_link = any(
        isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl))
        for entity in message.entities or []
    )

    if message.grouped_id:
        group_data = grouped_messages[message.grouped_id]
        group_data["messages"].append(message)
        group_data["timestamp"] = current_time

        if message.grouped_id in media_group_tasks:
            media_group_tasks[message.grouped_id].cancel()

        task = asyncio.create_task(handle_media_group_timeout(message.grouped_id))
        media_group_tasks[message.grouped_id] = task

    elif message.media and not contains_link:
        print(f"Обнаружено медиа: {message.media}")

        if isinstance(
            message.media, MessageMediaDocument
        ) and message.media.document.mime_type.startswith("video"):
            # Отправляем видео как "кружочек"
            await download_and_send_as_circle(message, message.media)
        else:
            await download_media_and_send(message, message.media, message.raw_text)

    elif message.raw_text or contains_link:
        await send_message_with_retries(
            client,
            target_channel_id,
            message.raw_text,
            parse_mode="html",
        )

async def main():
    # Подключаем роутер бота и запускаем polling
    dp.include_router(router)
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # Удаляем временный файл сессии
        if os.path.exists(session_file):
            os.remove(session_file)
            print(f"Удален файл сессии: {session_file}")

        # Удаляем временную папку, если она пустая
        if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Удалена временная папка: {temp_dir}")
