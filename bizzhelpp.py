import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# Импортируем админ-модуль
from admin_panel import setup_admin_handlers, admin_menu

API_TOKEN = "8302199284:AAHLD2P9hZZ9swbIgVE9qqlqbILz-417hZ8"
ADMIN_ID = (785219206, 891991569)  # Кортеж с двумя ID администраторов

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# Настраиваем админ-обработчики с передачей кортежа ADMIN_ID
setup_admin_handlers(dp, ADMIN_ID)

# Создаем папки для фото если их нет
os.makedirs("Photo1", exist_ok=True)
os.makedirs("Photo2", exist_ok=True)

conn = sqlite3.connect("Bookings.db")
cursor = conn.cursor()

# Проверка и добавление отсутствующих колонок
cursor.execute("PRAGMA table_info(classes)")
columns = [col[1] for col in cursor.fetchall()]
if "capacity" not in columns:
    try:
        cursor.execute("ALTER TABLE classes ADD COLUMN capacity INTEGER DEFAULT 1")
    except Exception:
        pass
if "class_type" not in columns:
    try:
        cursor.execute("ALTER TABLE classes ADD COLUMN class_type TEXT DEFAULT 'Обычное занятие'")
    except Exception:
        pass

# Проверяем и добавляем колонку photo_path в таблицу content если её нет
cursor.execute("PRAGMA table_info(content)")
content_columns = [col[1] for col in cursor.fetchall()]
if "photo_path" not in content_columns:
    try:
        cursor.execute("ALTER TABLE content ADD COLUMN photo_path TEXT")
    except Exception:
        pass

conn.commit()

# В разделе создания таблиц добавьте:
cursor.execute("""CREATE TABLE IF NOT EXISTS content (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    photo_path TEXT
                )""")

# Добавьте начальные данные, если их нет
cursor.execute(
    "INSERT OR IGNORE INTO content (key, value, photo_path) VALUES ('about_classes', '🧘 У нас разные форматы занятий: дыхательные практики, растяжка, медитация.', NULL)")
cursor.execute(
    "INSERT OR IGNORE INTO content (key, value, photo_path) VALUES ('announcement', '📢 Следите за анонсами занятий в этом чате.', NULL)")
conn.commit()

# Создание таблиц
cursor.execute("""CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    date TEXT,
                    time TEXT
                )""")
cursor.execute("""CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    time TEXT,
                    capacity INTEGER DEFAULT 1,
                    class_type TEXT DEFAULT 'Обычное занятие'
                )""")
conn.commit()

last_message = {}


# Функции преобразования формата даты
def format_date_display(db_date):
    """Преобразует дату из формата БД (YYYY-MM-DD) в формат отображения (DD.MM.YYYY)"""
    try:
        if db_date:
            date_obj = datetime.strptime(db_date, "%Y-%m-%d")
            return date_obj.strftime("%d.%m.%Y")
        return db_date
    except ValueError:
        return db_date


def format_date_storage(display_date):
    """Преобразует дату из формат отображения (DD.MM.YYYY) в формат БД (YYYY-MM-DD)"""
    try:
        if display_date:
            date_obj = datetime.strptime(display_date, "%d.%m.%Y")
            return date_obj.strftime("%Y-%m-%d")
        return display_date
    except ValueError:
        return display_date


# Функция для отправки уведомлений администраторам
async def notify_admin(message_text):
    """Отправляет уведомление всем администраторам"""
    for admin_id in ADMIN_ID:
        try:
            await bot.send_message(admin_id, message_text)
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")


# Функция для удаления предыдущего сообщения пользователя
async def delete_previous_user_message(user_id: int):
    """Удаляет предыдущее сообщение бота у пользователя"""
    if user_id in last_message:
        chat_id, message_id = last_message[user_id]
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении предыдущего сообщения: {e}")
        # Удаляем запись о сообщении независимо от результата
        last_message.pop(user_id, None)


# Функции для получения текста и фото
def get_about_classes_data():
    cursor.execute("SELECT value, photo_path FROM content WHERE key = 'about_classes'")
    result = cursor.fetchone()
    if result:
        text, photo_filename = result
        if photo_filename:
            photo_path = os.path.join("Photo1", photo_filename)
            # Проверяем существование файла
            if os.path.exists(photo_path):
                return text, photo_path
            else:
                logging.warning(f"Файл не найден: {photo_path}")
        return text, None
    return "🧘 У нас разные форматы занятий: дыхательные практики, растяжка, медитация.", None


def get_announcement_data():
    cursor.execute("SELECT value, photo_path FROM content WHERE key = 'announcement'")
    result = cursor.fetchone()
    if result:
        text, photo_filename = result
        if photo_filename:
            photo_path = os.path.join("Photo2", photo_filename)
            # Проверяем существование файла
            if os.path.exists(photo_path):
                return text, photo_path
            else:
                logging.warning(f"Файл не найден: {photo_path}")
        return text, None
    return "📢 Следите за анонсами занятий в этом чате.", None


async def handle_text_response(callback: CallbackQuery, text: str):
    """Обрабатывает текстовый ответ и сохраняет сообщение"""
    try:
        msg = await callback.message.edit_text(text, reply_markup=main_menu())
        last_message[callback.from_user.id] = (msg.chat.id, msg.message_id)
    except Exception:
        # Если редактирование не удалось, отправляем новое сообщение
        msg = await callback.message.answer(text, reply_markup=main_menu())
        last_message[callback.from_user.id] = (msg.chat.id, msg.message_id)


async def send_or_edit_single(user_id: int, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    """
    Попытаться отредактировать уже существующее 'главное' сообщение пользователя,
    иначе отправить новое и сохранить его в last_message.
    """
    if user_id in last_message:
        old_chat_id, old_message_id = last_message[user_id]
        try:
            # Пытаемся отредактировать существующее сообщение
            msg = await bot.edit_message_text(text, chat_id=old_chat_id, message_id=old_message_id,
                                              reply_markup=reply_markup, parse_mode="HTML")
            last_message[user_id] = (msg.chat.id, msg.message_id)
            return
        except Exception:
            # Если редактирование не удалось, удаляем старое сообщение и отправляем новое
            try:
                await bot.delete_message(old_chat_id, old_message_id)
            except Exception:
                pass
            # Удаляем запись о старом сообщении
            last_message.pop(user_id, None)

    # Отправляем новое сообщение
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    last_message[user_id] = (msg.chat.id, msg.message_id)


def main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Запись на занятие", callback_data="book_class"),
            InlineKeyboardButton(text="🧘 О занятиях", callback_data="about_classes")
        ],
        [
            InlineKeyboardButton(text="📖 Мои занятия", callback_data="my_bookings"),
            InlineKeyboardButton(text="❌ Отмена записи", callback_data="cancel_booking")
        ],
        [
            InlineKeyboardButton(text="📢 Анонс мероприятий", callback_data="announcement"),
            InlineKeyboardButton(text="💬 Поддержка", callback_data="support")
        ]
    ])
    return keyboard


def cancel_keyboard(user_id: int):
    cursor.execute("SELECT id, date, time FROM bookings WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    buttons = []
    for r in rows:
        display_date = format_date_display(r[1])  # Преобразуем формат даты
        btn = InlineKeyboardButton(
            text=f"{display_date} {r[2]}", callback_data=f"cancel:{r[0]}"
        )
        buttons.append([btn])
    if not buttons:
        buttons.append([InlineKeyboardButton(text="Нет записей", callback_data="no_booking")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="go_user_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def available_classes_keyboard():
    cursor.execute("""
        SELECT DISTINCT date FROM classes
        ORDER BY date
    """)
    rows = cursor.fetchall()
    if not rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Нет доступных занятий", callback_data="no_classes")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="go_user_menu")]
        ])
        return kb

    buttons = []
    for row in rows:
        display_date = format_date_display(row[0])  # Преобразуем формат
        buttons.append(InlineKeyboardButton(
            text=display_date,
            callback_data=f"date:{row[0]}"  # В callback_data оставляем исходный формат
        ))

    inline_keyboard = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="go_user_menu")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def available_times_keyboard(selected_date: str):
    cursor.execute("""
        SELECT c.time, c.capacity - COUNT(b.id) as free_slots, c.class_type
        FROM classes c
        LEFT JOIN bookings b ON c.date=b.date AND c.time=b.time
        WHERE c.date=?
        GROUP BY c.id
        HAVING free_slots > 0
        ORDER BY c.time
    """, (selected_date,))
    rows = cursor.fetchall()
    if not rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Нет доступных слотов", callback_data="no_times")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="book_class")]
        ])
        return kb
    buttons = [
        InlineKeyboardButton(
            text=f"{r[0]} • {r[2]} ({r[1]} мест)",
            callback_data=f"time:{selected_date}:{r[0]}"
        )
        for r in rows
    ]
    inline_keyboard = [buttons[i:i + 1] for i in range(0, len(buttons), 1)]
    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="book_class")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


@dp.message(Command("start"))
async def start(message: Message):
    try:
        await message.delete()
    except Exception:
        pass
    text = f"""Привет, {message.from_user.first_name}! 👋
Меня зовут Йога-Бот, и я помогу тебе записаться на занятия. 🧘‍♀️
Выбери нужный пункт в меню ниже:"""
    await send_or_edit_single(message.from_user.id, message.chat.id, text, main_menu())


@dp.message(Command("admin"))
async def admin_panel_cmd(message: Message):
    try:
        await message.delete()
    except Exception:
        pass
    if message.from_user.id not in ADMIN_ID:
        await send_or_edit_single(message.from_user.id, message.chat.id, "❌ У тебя нет доступа к админ-панели.", None)
        return
    await send_or_edit_single(message.from_user.id, message.chat.id, "Админ-панель:", admin_menu())


# Обработчики для about_classes и announcement
@dp.callback_query(lambda c: c.data == "about_classes")
async def about_classes(callback: CallbackQuery):
    # Удаляем предыдущее сообщение бота
    await delete_previous_user_message(callback.from_user.id)

    text, photo_path = get_about_classes_data()

    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            msg = await callback.message.answer_photo(photo, caption=text, reply_markup=main_menu())
            # Сохраняем новое сообщение
            last_message[callback.from_user.id] = (msg.chat.id, msg.message_id)
        except Exception as e:
            logging.error(f"Ошибка при отправке фото: {e}")
            await handle_text_response(callback, text)
    else:
        await handle_text_response(callback, text)


@dp.callback_query(lambda c: c.data == "announcement")
async def announcement(callback: CallbackQuery):
    # Удаляем предыдущее сообщение бота
    await delete_previous_user_message(callback.from_user.id)

    text, photo_path = get_announcement_data()

    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            msg = await callback.message.answer_photo(photo, caption=text, reply_markup=main_menu())
            # Сохраняем новое сообщение
            last_message[callback.from_user.id] = (msg.chat.id, msg.message_id)
        except Exception as e:
            logging.error(f"Ошибка при отправке фото: {e}")
            await handle_text_response(callback, text)
    else:
        await handle_text_response(callback, text)


@dp.callback_query()
async def handle_menu(callback: CallbackQuery):
    data = callback.data or ""
    user_id = callback.from_user.id
    await callback.answer()

    if data == "book_class":
        kb = available_classes_keyboard()
        try:
            await callback.message.edit_text("Выбери дату занятия:", reply_markup=kb)
            last_message[user_id] = (callback.message.chat.id, callback.message.message_id)
        except Exception:
            await send_or_edit_single(user_id, callback.message.chat.id, "Выбери дату занятия:", kb)
        return

    if data.startswith("date:"):
        selected_date_db = data.split(":", 1)[1]
        selected_date_display = format_date_display(selected_date_db)  # Преобразуем для отображения
        kb = available_times_keyboard(selected_date_db)
        try:
            await callback.message.edit_text(
                f"Вы выбрали дату: {selected_date_display}. Теперь выбери время:", reply_markup=kb)
            last_message[user_id] = (callback.message.chat.id, callback.message.message_id)
        except Exception:
            await send_or_edit_single(user_id, callback.message.chat.id,
                                      f"Вы выбрали дату: {selected_date_display}. Теперь выбери время:", kb)
        return

    if data.startswith("time:"):
        parts = data.split(":", 2)
        if len(parts) < 3:
            try:
                await callback.message.edit_text("❌ Ошибка при выборе времени. Попробуйте снова.",
                                                 reply_markup=main_menu())
                last_message[user_id] = (callback.message.chat.id, callback.message.message_id)
            except Exception:
                await send_or_edit_single(user_id, callback.message.chat.id,
                                          "❌ Ошибка при выборе времени. Попробуйте снова.", main_menu())
            return

        _, selected_date_db, selected_time = parts
        selected_date_display = format_date_display(selected_date_db)  # Преобразуем для отображения

        cursor.execute("SELECT id FROM bookings WHERE user_id=? AND date=? AND time=?",
                       (user_id, selected_date_db, selected_time))
        if cursor.fetchone():
            try:
                await callback.message.edit_text("❌ Вы уже записаны на это занятие!", reply_markup=main_menu())
                last_message[user_id] = (callback.message.chat.id, callback.message.message_id)
            except Exception:
                await send_or_edit_single(user_id, callback.message.chat.id, "❌ Вы уже записаны на это занятие!",
                                          main_menu())
            return

        cursor.execute("SELECT capacity, class_type FROM classes WHERE date=? AND time=?",
                       (selected_date_db, selected_time))
        result = cursor.fetchone()
        if not result:
            try:
                await callback.message.edit_text("❌ Ошибка: занятие не найдено. Попробуйте выбрать другое.",
                                                 reply_markup=main_menu())
                last_message[user_id] = (callback.message.chat.id, callback.message.message_id)
            except Exception:
                await send_or_edit_single(user_id, callback.message.chat.id,
                                          "❌ Ошибка: занятие не найдено. Попробуйте выбрать другое.", main_menu())
            return

        capacity, class_type = result
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE date=? AND time=?", (selected_date_db, selected_time))
        count = cursor.fetchone()[0]

        if count >= capacity:
            try:
                await callback.message.edit_text("❌ На это занятие больше нет мест!", reply_markup=main_menu())
            except Exception:
                await send_or_edit_single(user_id, callback.message.chat.id, "❌ На это занятие больше нет мест!",
                                          main_menu())
            return

        cursor.execute(
            "INSERT INTO bookings (user_id, username, date, time) VALUES (?, ?, ?, ?)",
            (user_id, callback.from_user.username, selected_date_db, selected_time)
        )
        conn.commit()

        # Отправляем уведомление администраторам о новой записи
        admin_message = (
            f"✅ Новая запись на занятие:\n"
            f"👤 Пользователь: @{callback.from_user.username or 'нет username'} (ID: {user_id})\n"
            f"📅 Дата: {selected_date_display}\n"
            f"⏰ Время: {selected_time}\n"
            f"🧘 Тип: {class_type}"
        )
        await notify_admin(admin_message)

        try:
            await callback.message.edit_text(
                f"✅ Вы записаны на занятие {selected_date_display} в {selected_time} ({class_type})!",
                reply_markup=main_menu())
        except Exception:
            await send_or_edit_single(user_id, callback.message.chat.id,
                                      f"✅ Вы записаны на занятие {selected_date_display} в {selected_time} ({class_type})!",
                                      main_menu())
        return

    if data == "cancel_booking":
        kb = cancel_keyboard(user_id)
        try:
            await callback.message.edit_text("Выберите запись для отмены:", reply_markup=kb)
        except Exception:
            await send_or_edit_single(user_id, callback.message.chat.id, "Выберите запись для отмены:", kb)
        return

    if data.startswith("cancel:"):
        booking_id = int(data.split(":", 1)[1])

        # Получаем информацию о записи перед удалением
        cursor.execute("SELECT user_id, username, date, time FROM bookings WHERE id=?", (booking_id,))
        booking_info = cursor.fetchone()

        if booking_info:
            user_id, username, date, time = booking_info
            display_date = format_date_display(date)

            # Удаляем запись
            cursor.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
            conn.commit()

            # Отправляем уведомление администраторам об отмене
            admin_message = (
                f"❌ Отмена записи на занятие:\n"
                f"👤 Пользователь: @{username or 'нет username'} (ID: {user_id})\n"
                f"📅 Дата: {display_date}\n"
                f"⏰ Время: {time}"
            )
            await notify_admin(admin_message)

        try:
            await callback.message.edit_text("✅ Запись успешно отменена.", reply_markup=main_menu())
        except Exception:
            await send_or_edit_single(user_id, callback.message.chat.id, "✅ Запись успешно отменена.", main_menu())
        return

    if data == "my_bookings":
        cursor.execute("""
            SELECT b.date, b.time, c.class_type
            FROM bookings b
            LEFT JOIN classes c ON b.date=c.date AND b.time=c.time
            WHERE b.user_id=?
            ORDER BY b.date, b.time
        """, (user_id,))
        rows = cursor.fetchall()
        if not rows:
            try:
                await callback.message.edit_text("📖 У вас пока нет записей на занятия.", reply_markup=main_menu())
            except Exception:
                await send_or_edit_single(user_id, callback.message.chat.id, "📖 У вас пока нет записей на занятия.",
                                          main_menu())
        else:
            text = "📖 <b>Ваши занятия:</b>\n\n"
            for r in rows:
                display_date = format_date_display(r[0])  # Преобразуем формат даты
                text += f"📅 {display_date} ⏰ {r[1]} • {r[2] if r[2] else 'Занятие'}\n"
            try:
                await callback.message.edit_text(text, reply_markup=main_menu())
            except Exception:
                await send_or_edit_single(user_id, callback.message.chat.id, text, main_menu())
        return

    if data == "support":
        try:
            await callback.message.edit_text("💬 Для поддержки напишите мне @danakushu.", reply_markup=main_menu())
        except Exception:
            await send_or_edit_single(user_id, callback.message.chat.id, "💬 Для поддержки напишите мне @danakushu.",
                                      main_menu())
        return

    if data == "go_user_menu":
        try:
            await callback.message.edit_text(f"Привет, {callback.from_user.first_name}! 👋\n\nВыберите пункт:",
                                             reply_markup=main_menu())
        except Exception:
            await send_or_edit_single(user_id, callback.message.chat.id,
                                      f"Привет, {callback.from_user.first_name}! 👋\n\nВыберите пункт:", main_menu())
        return


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
