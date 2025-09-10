from aiogram import Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import sqlite3
import os
import logging
from datetime import datetime

conn = sqlite3.connect("Bookings.db")
cursor = conn.cursor()


class AdminAddClass(StatesGroup):
    month = State()
    day = State()
    time = State()
    capacity = State()
    class_type = State()


class AdminRemoveClass(StatesGroup):
    select_class = State()
    confirm_notification = State()
    notification_text = State()


class EditContent(StatesGroup):
    select_type = State()
    edit_text = State()
    add_photo = State()


def admin_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить занятие", callback_data="admin_add_class"),
            InlineKeyboardButton(text="➖ Убрать занятие", callback_data="admin_remove_class")
        ],
        [
            InlineKeyboardButton(text="📋 Актуальные занятия", callback_data="admin_view_classes"),
            InlineKeyboardButton(text="👥 Просмотр записей", callback_data="admin_view_bookings")
        ],
        [
            InlineKeyboardButton(text="✏️ Редактировать контент", callback_data="admin_edit_content"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="go_user_menu")
        ]
    ])
    return keyboard


def get_about_classes_data():
    cursor.execute("SELECT value, photo_path FROM content WHERE key = 'about_classes'")
    result = cursor.fetchone()
    if result:
        text, photo_filename = result
        if photo_filename:
            photo_path = os.path.join("Photo1", photo_filename)
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
            if os.path.exists(photo_path):
                return text, photo_path
            else:
                logging.warning(f"Файл не найден: {photo_path}")
        return text, None
    return "📢 Следите за анонсами занятий в этом чате.", None


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
    """Преобразует дату из формата отображения (DD.MM.YYYY) в формат БД (YYYY-MM-DD)"""
    try:
        if display_date:
            date_obj = datetime.strptime(display_date, "%d.%m.%Y")
            return date_obj.strftime("%Y-%m-%d")
        return display_date
    except ValueError:
        return display_date


async def delete_previous_messages(message: Message, state: FSMContext):
    """Удаляет предыдущие служебные сообщения из состояния"""
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])

    for msg_id in messages_to_delete:
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения {msg_id}: {e}")

    # Сохраняем текущее сообщение для будущего удаления
    messages_to_delete.append(message.message_id)
    await state.update_data(messages_to_delete=messages_to_delete)


def setup_admin_handlers(dp: Dispatcher, admin_ids: tuple):
    """Настройка обработчиков админ-панели"""

    @dp.callback_query(lambda c: c.data == "admin_add_class")
    async def admin_add_class_start(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа к этой функции.")
            return

        # Инициализируем список сообщений для удаления
        await state.update_data(messages_to_delete=[])

        months = [str(i) for i in range(1, 13)]
        buttons = [InlineKeyboardButton(text=m, callback_data=f"month:{m}") for m in months]
        inline_keyboard = [buttons[i:i + 4] for i in range(0, len(buttons), 4)]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        try:
            await callback.message.edit_text("Выберите месяц занятия:", reply_markup=keyboard)
        except Exception:
            msg = await callback.message.answer("Выберите месяц занятия:", reply_markup=keyboard)
            # Сохраняем ID сообщения для будущего удаления
            data = await state.get_data()
            messages_to_delete = data.get('messages_to_delete', [])
            messages_to_delete.append(msg.message_id)
            await state.update_data(messages_to_delete=messages_to_delete)

        await state.set_state(AdminAddClass.month)

    @dp.callback_query(AdminAddClass.month)
    async def admin_add_class_month(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        parts = (callback.data or "").split(":", 1)
        if len(parts) < 2 or not parts[1]:
            await callback.message.edit_text("❌ Ошибка выбора месяца. Попробуйте заново.", reply_markup=admin_menu())
            await state.clear()
            return

        selected_month = parts[1]
        await state.update_data(month=selected_month)

        days = [str(i) for i in range(1, 32)]
        buttons = [InlineKeyboardButton(text=d, callback_data=f"day:{d}") for d in days]
        inline_keyboard = [buttons[i:i + 7] for i in range(0, len(buttons), 7)]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        try:
            await callback.message.edit_text("Выберите день занятия:", reply_markup=keyboard)
        except Exception:
            msg = await callback.message.answer("Выберите день занятия:", reply_markup=keyboard)
            # Сохраняем ID сообщения для будущего удаления
            data = await state.get_data()
            messages_to_delete = data.get('messages_to_delete', [])
            messages_to_delete.append(msg.message_id)
            await state.update_data(messages_to_delete=messages_to_delete)

        await state.set_state(AdminAddClass.day)

    @dp.callback_query(AdminAddClass.day)
    async def admin_add_class_day(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        parts = (callback.data or "").split(":", 1)
        if len(parts) < 2 or not parts[1]:
            await callback.message.edit_text("❌ Ошибка выбора дня. Попробуйте заново.", reply_markup=admin_menu())
            await state.clear()
            return

        selected_day = parts[1]
        await state.update_data(day=selected_day)

        # Получаем год, месяц и день для формирования даты
        data = await state.get_data()
        month = data.get('month')
        day = selected_day
        year = datetime.now().year

        # Формируем дату в формате для отображения
        display_date = f"{int(day):02d}.{int(month):02d}.{year}"
        await state.update_data(display_date=display_date)

        # Удаляем предыдущие сообщения
        await delete_previous_messages(callback.message, state)

        msg = await callback.message.answer("Введите время занятия (например: 19:30):")
        # Сохраняем ID сообщения для будущего удаления
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(msg.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)

        await state.set_state(AdminAddClass.time)

    @dp.message(AdminAddClass.time)
    async def admin_add_class_time(message: Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in admin_ids:
            return

        # Удаляем предыдущие сообщения и само сообщение пользователя
        await delete_previous_messages(message, state)
        try:
            await message.delete()
        except Exception:
            pass

        try:
            datetime.strptime(message.text, "%H:%M")
        except Exception:
            msg = await message.answer("❌ Ошибка: введите время в формате ЧЧ:ММ (например 19:30). Попробуйте снова:")
            # Сохраняем ID сообщения для будущего удаления
            data = await state.get_data()
            messages_to_delete = data.get('messages_to_delete', [])
            messages_to_delete.append(msg.message_id)
            await state.update_data(messages_to_delete=messages_to_delete)
            return

        await state.update_data(time=message.text)

        msg = await message.answer("Введите количество участников для занятия:")
        # Сохраняем ID сообщения для будущего удаления
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(msg.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)

        await state.set_state(AdminAddClass.capacity)

    @dp.message(AdminAddClass.capacity)
    async def admin_add_class_capacity(message: Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in admin_ids:
            return

        # Удаляем предыдущие сообщения и само сообщение пользователя
        await delete_previous_messages(message, state)
        try:
            await message.delete()
        except Exception:
            pass

        try:
            capacity = int(message.text)
        except ValueError:
            msg = await message.answer("❌ Ошибка: нужно ввести число. Попробуйте снова.")
            # Сохраняем ID сообщения для будущего удаления
            data = await state.get_data()
            messages_to_delete = data.get('messages_to_delete', [])
            messages_to_delete.append(msg.message_id)
            await state.update_data(messages_to_delete=messages_to_delete)
            return

        await state.update_data(capacity=capacity)

        msg = await message.answer("Теперь введите тип занятия (например: Йога-нидра, Растяжка, Медитация):")
        # Сохраняем ID сообщения для будущего удаления
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(msg.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)

        await state.set_state(AdminAddClass.class_type)

    @dp.message(AdminAddClass.class_type)
    async def admin_add_class_type(message: Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in admin_ids:
            return

        class_type = message.text
        # Удаляем предыдущие сообщения и само сообщение пользователя
        await delete_previous_messages(message, state)
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        if not all(k in data for k in ("month", "day", "time", "capacity", "display_date")):
            await message.answer("❌ Ошибка: данные занятия неполные. Начните заново.", reply_markup=admin_menu())
            await state.clear()
            return

        # Преобразуем дату из формат отображения в формат хранения
        display_date = data.get('display_date')
        class_date = format_date_storage(display_date)

        time_text = data['time']
        capacity = data['capacity']

        cursor.execute("INSERT INTO classes (date, time, capacity, class_type) VALUES (?, ?, ?, ?)",
                       (class_date, time_text, capacity, class_type))
        conn.commit()

        await message.answer(f"✅ Занятие добавлено: {display_date} в {time_text} ({class_type}), мест: {capacity}",
                             reply_markup=admin_menu())
        await state.clear()

    @dp.callback_query(lambda c: c.data == "admin_view_classes")
    async def admin_view_classes(callback: CallbackQuery):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа к этой функции.")
            return

        cursor.execute("SELECT date, time, class_type, capacity FROM classes ORDER BY date, time")
        rows = cursor.fetchall()

        if not rows:
            await callback.message.edit_text("❌ Нет актуальных занятий.", reply_markup=admin_menu())
            return

        text = "📋 <b>Список занятий:</b>\n\n"
        for r in rows:
            display_date = format_date_display(r[0])
            text += f"📅 {display_date} ⏰ {r[1]} • {r[2]} (мест: {r[3]})\n"

        await callback.message.edit_text(text, reply_markup=admin_menu())

    @dp.callback_query(lambda c: c.data == "admin_view_bookings")
    async def admin_view_bookings(callback: CallbackQuery):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа к этой функции.")
            return

        # Получаем список всех занятий
        cursor.execute("""
            SELECT c.id, c.date, c.time, c.class_type, c.capacity, 
                   COUNT(b.id) as booked_count
            FROM classes c
            LEFT JOIN bookings b ON c.date = b.date AND c.time = b.time
            GROUP BY c.id
            ORDER BY c.date, c.time
        """)
        rows = cursor.fetchall()

        if not rows:
            await callback.message.edit_text("❌ Нет актуальных занятий.", reply_markup=admin_menu())
            return

        # Создаем кнопки для каждого занятия
        keyboard_buttons = []
        for r in rows:
            class_id, date, time, class_type, capacity, booked_count = r
            display_date = format_date_display(date)
            button_text = f"{display_date} {time} • {class_type} • {booked_count}/{capacity}"
            keyboard_buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_booking_details:{class_id}"
            )])

        # Добавляем кнопку "Назад"
        keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text("📊 Выберите занятие для просмотра записей:", reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data.startswith("view_booking_details:"))
    async def admin_view_booking_details(callback: CallbackQuery):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа к этой функции.")
            return

        # Извлекаем ID занятия из callback_data
        class_id = int(callback.data.split(":")[1])

        # Получаем информацию о занятии
        cursor.execute("SELECT date, time, class_type, capacity FROM classes WHERE id=?", (class_id,))
        class_info = cursor.fetchone()

        if not class_info:
            await callback.message.edit_text("❌ Занятие не найдено.", reply_markup=admin_menu())
            return

        date, time, class_type, capacity = class_info
        display_date = format_date_display(date)

        # Получаем список записавшихся пользователей
        cursor.execute("""
            SELECT username, user_id 
            FROM bookings 
            WHERE date=? AND time=? 
            ORDER BY id
        """, (date, time))
        bookings = cursor.fetchall()

        # Формируем текст сообщения
        text = f"📊 <b>Информация о занятии:</b>\n\n"
        text += f"📅 Дата: {display_date}\n"
        text += f"⏰ Время: {time}\n"
        text += f"🧘 Тип: {class_type}\n"
        text += f"👥 Записано: {len(bookings)}/{capacity}\n\n"

        if bookings:
            text += "📋 <b>Список записавшихся:</b>\n\n"
            for i, (username, user_id) in enumerate(bookings, 1):
                username_display = f"@{username}" if username else f"ID: {user_id}"
                text += f"{i}. {username_display}\n"
        else:
            text += "❌ На это занятие еще никто не записался."

        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_view_bookings")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="admin_back")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data == "admin_remove_class")
    async def admin_remove_class(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа к этой функции.")
            return

        # Инициализируем список сообщений для удаления
        await state.update_data(messages_to_delete=[])

        cursor.execute("SELECT id, date, time, class_type FROM classes ORDER by date, time")
        rows = cursor.fetchall()

        if not rows:
            await callback.message.edit_text("❌ Нет занятий для удаления.", reply_markup=admin_menu())
            return

        keyboard_buttons = []
        for r in rows:
            class_id, date, time, class_type = r
            display_date = format_date_display(date)
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{display_date} {time} • {class_type}",
                callback_data=f"remove_class:{class_id}"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text("Выберите занятие для удаления:", reply_markup=keyboard)
        await state.set_state(AdminRemoveClass.select_class)

    @dp.callback_query(AdminRemoveClass.select_class)
    async def admin_remove_class_select(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа.")
            await state.clear()
            return

        parts = (callback.data or "").split(":", 1)
        if len(parts) < 2:
            await callback.message.edit_text("❌ Ошибка при выборе. Попробуйте снова.", reply_markup=admin_menu())
            await state.clear()
            return

        class_id = int(parts[1])
        cursor.execute("SELECT date, time, class_type FROM classes WHERE id=?", (class_id,))
        class_info = cursor.fetchone()

        if not class_info:
            await callback.message.edit_text("❌ Ошибка: занятие не найдено.", reply_markup=admin_menu())
            await state.clear()
            return

        class_date, class_time, class_type = class_info
        display_date = format_date_display(class_date)

        # Сохраняем информацию о занятии для возможной отправки уведомления
        await state.update_data(
            class_date=class_date,
            class_time=class_time,
            class_type=class_type,
            display_date=display_date
        )

        # Получаем список пользователей, записанных на это занятие
        cursor.execute("SELECT user_id FROM bookings WHERE date=? AND time=?", (class_date, class_time))
        bookings = cursor.fetchall()
        user_ids = [booking[0] for booking in bookings]

        # Сохраняем ID пользователей для возможной отправки уведомления
        await state.update_data(user_ids=user_ids)

        # Спрашиваем, отправить ли уведомление об отмене
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, отправить уведомление", callback_data="send_notification:yes")],
            [InlineKeyboardButton(text="❌ Нет, просто удалить", callback_data="send_notification:no")]
        ])

        await callback.message.edit_text(
            f"Отправить уведомление об отмене занятия {display_date} в {class_time} ({class_type})?",
            reply_markup=keyboard
        )
        await state.set_state(AdminRemoveClass.confirm_notification)

    @dp.callback_query(AdminRemoveClass.confirm_notification)
    async def admin_confirm_notification(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа.")
            await state.clear()
            return

        parts = (callback.data or "").split(":", 1)
        if len(parts) < 2:
            await callback.message.edit_text("❌ Ошибка. Попробуйте снова.", reply_markup=admin_menu())
            await state.clear()
            return

        action = parts[1]
        data = await state.get_data()
        class_date = data.get('class_date')
        class_time = data.get('class_time')
        class_type = data.get('class_type')
        display_date = data.get('display_date')
        user_ids = data.get('user_ids', [])

        # Удаляем занятие и записи
        cursor.execute("DELETE FROM bookings WHERE date=? AND time=?", (class_date, class_time))
        cursor.execute("DELETE FROM classes WHERE date=? AND time=?", (class_date, class_time))
        conn.commit()

        if action == "yes":
            # Удаляем предыдущие сообщения
            await delete_previous_messages(callback.message, state)

            msg = await callback.message.answer("Введите текст уведомления об отмене занятия:")
            # Сохраняем ID сообщения для будущего удаления
            data = await state.get_data()
            messages_to_delete = data.get('messages_to_delete', [])
            messages_to_delete.append(msg.message_id)
            await state.update_data(messages_to_delete=messages_to_delete)

            await state.set_state(AdminRemoveClass.notification_text)
        else:
            # Просто удаляем без уведомления
            await callback.message.edit_text(
                f"✅ Занятие {display_date} {class_time} ({class_type}) удалено вместе с записями.",
                reply_markup=admin_menu()
            )
            await state.clear()

    @dp.message(AdminRemoveClass.notification_text)
    async def admin_send_notification(message: Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in admin_ids:
            await state.clear()
            return

        notification_text = message.text
        # Удаляем предыдущие сообщения и само сообщение пользователя
        await delete_previous_messages(message, state)
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        class_date = data.get('class_date')
        class_time = data.get('class_time')
        class_type = data.get('class_type')
        display_date = data.get('display_date')
        user_ids = data.get('user_ids', [])

        # Отправляем уведомление всем пользователям
        success_count = 0
        fail_count = 0

        for user_id in user_ids:
            try:
                await message.bot.send_message(
                    user_id,
                    f"❌ Уведомление об отмене занятия:\n\n"
                    f"📅 Дата: {display_date}\n"
                    f"⏰ Время: {class_time}\n"
                    f"🧘 Тип: {class_type}\n\n"
                    f"{notification_text}"
                )
                success_count += 1
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
                fail_count += 1

        # Формируем отчет об отправке
        report_text = (
            f"✅ Занятие {display_date} {class_time} ({class_type}) удалено вместе с записи.\n\n"
            f"📊 Статус отправки уведомлений:\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Не удалось: {fail_count}"
        )

        await message.answer(report_text, reply_markup=admin_menu())
        await state.clear()

    @dp.callback_query(lambda c: c.data == "admin_edit_content")
    async def admin_edit_content(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа к этой функции.")
            return

        # Инициализируем список сообщений для удаления
        await state.update_data(messages_to_delete=[])

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘 Информация о занятиях", callback_data="edit_about")],
            [InlineKeyboardButton(text="📢 Анонс мероприятий", callback_data="edit_announcement")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ])

        await callback.message.edit_text("Что вы хотите отредактировать?", reply_markup=keyboard)
        await state.set_state(EditContent.select_type)

    @dp.callback_query(EditContent.select_type)
    async def admin_edit_content_select(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await callback.message.edit_text("❌ У тебя нет доступа.")
            await state.clear()
            return

        content_type = callback.data
        if content_type == "admin_back":
            await callback.message.edit_text("Админ-панель:", reply_markup=admin_menu())
            await state.clear()
            return

        # Получаем текущий текст
        if content_type == "edit_about":
            key = "about_classes"
            current_text, current_photo = get_about_classes_data()
            prompt = "Текущая информация о занятиях:\n\n" + current_text + "\n\nВведите новый текст:"
        elif content_type == "edit_announcement":
            key = "announcement"
            current_text, current_photo = get_announcement_data()
            prompt = "Текущий анонс:\n\n" + current_text + "\n\nВведите новый текст:"
        else:
            await callback.message.edit_text("❌ Неизвестный тип контента.", reply_markup=admin_menu())
            await state.clear()
            return

        await state.update_data(content_key=key, current_text=current_text, current_photo=current_photo)

        # Удаляем предыдущие сообщения
        await delete_previous_messages(callback.message, state)

        msg = await callback.message.answer(prompt)
        # Сохраняем ID сообщения для будущего удаления
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(msg.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)

        await state.set_state(EditContent.edit_text)

    @dp.message(EditContent.edit_text)
    async def admin_edit_content_save(message: Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in admin_ids:
            await state.clear()
            return

        # Удаляем предыдущие сообщения и само сообщение пользователя
        await delete_previous_messages(message, state)
        try:
            await message.delete()
        except Exception:
            pass

        data = await state.get_data()
        content_key = data.get('content_key')
        new_text = message.text

        if not content_key or not new_text:
            await message.answer("❌ Ошибка при сохранении. Попробуйте снова.", reply_markup=admin_menu())
            await state.clear()
            return

        await state.update_data(new_text=new_text)

        # Спрашиваем, хочет ли админ добавить фото
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, добавить фото", callback_data="add_photo_yes")],
            [InlineKeyboardButton(text="❌ Нет, только текст", callback_data="add_photo_no")]
        ])

        msg = await message.answer("Хотите добавить фото к этому контенту?", reply_markup=keyboard)
        # Сохраняем ID сообщения для будущего удаления
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(msg.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)

        await state.set_state(EditContent.add_photo)

    @dp.callback_query(EditContent.add_photo)
    async def admin_edit_content_photo_choice(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            await state.clear()
            return

        data = await state.get_data()
        content_key = data.get('content_key')
        new_text = data.get('new_text')

        if callback.data == "add_photo_no":
            # Сохраняем только текст (удаляем фото если было)
            cursor.execute("UPDATE content SET value = ?, photo_path = NULL WHERE key = ?", (new_text, content_key))
            conn.commit()

            if content_key == "about_classes":
                success_message = "✅ Информация о занятиях успешно обновлена (без фото)!"
            else:
                success_message = "✅ Анонс мероприятий успешно обновлен (без фото)!"

            await callback.message.edit_text(success_message, reply_markup=admin_menu())
            await state.clear()
            return

        # Если админ хочет добавить фото
        if content_key == "about_classes":
            folder = "Photo1"
        else:
            folder = "Photo2"

        # Удаляем предыдущие сообщения
        await delete_previous_messages(callback.message, state)

        msg = await callback.message.answer(f"📸 Отправьте фото для добавления. Оно будет сохранено в папку {folder}/")
        # Сохраняем ID сообщения для будущего удаления
        data = await state.get_data()
        messages_to_delete = data.get('messages_to_delete', [])
        messages_to_delete.append(msg.message_id)
        await state.update_data(messages_to_delete=messages_to_delete)

        await state.update_data(photo_folder=folder)

    @dp.message(EditContent.add_photo)
    async def admin_edit_content_photo_save(message: Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in admin_ids:
            await state.clear()
            return

        if not message.photo:
            # Удаляем предыдущие сообщения
            await delete_previous_messages(message, state)

            msg = await message.answer("❌ Пожалуйста, отправьте фото. Отправьте фото или нажмите /cancel для отмены.")
            # Сохраняем ID сообщения для будущего удаления
            data = await state.get_data()
            messages_to_delete = data.get('messages_to_delete', [])
            messages_to_delete.append(msg.message_id)
            await state.update_data(messages_to_delete=messages_to_delete)
            return

        try:
            # Удаляем предыдущие сообщения и само сообщение с фото
            await delete_previous_messages(message, state)
            try:
                await message.delete()
            except Exception:
                pass

            data = await state.get_data()
            content_key = data.get('content_key')
            new_text = data.get('new_text')
            folder = data.get('photo_folder')

            # Удаляем все старые файлы в папке
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logging.error(f"Ошибка при удалении файла {file_path}: {e}")

            # Получаем самое большое фото (лучшее качество)
            photo = message.photo[-1]
            file_id = photo.file_id
            file = await message.bot.get_file(file_id)
            file_path = file.file_path

            # Создаем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_filename = f"{content_key}_{timestamp}.jpg"
            photo_path = os.path.join(folder, photo_filename)

            # Скачиваем и сохраняем фото
            await message.bot.download_file(file_path, photo_path)

            # Сохраняем в базу данных только имя файла
            cursor.execute("UPDATE content SET value = ?, photo_path = ? WHERE key = ?",
                           (new_text, photo_filename, content_key))
            conn.commit()

            if content_key == "about_classes":
                success_message = "✅ Информация о занятиях успешно обновлена с фото!"
            else:
                success_message = "✅ Анонс мероприятий успешно обновлен с фото!"

            await message.answer(success_message, reply_markup=admin_menu())
            await state.clear()

        except Exception as e:
            await message.answer(f"❌ Ошибка при сохранении фото: {str(e)}", reply_markup=admin_menu())
            await state.clear()

    @dp.callback_query(lambda c: c.data == "admin_back")
    async def admin_back(callback: CallbackQuery, state: FSMContext):
        await callback.answer()
        if callback.from_user.id not in admin_ids:
            return

        await callback.message.edit_text("Админ-панель:", reply_markup=admin_menu())
        await state.clear()
