import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ============================================================
# SETTINGS
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

SHOP_CHANNEL = "@ruby_shop_dn"
SHOP_CHANNEL_URL = "https://t.me/ruby_shop_dn"
DB_FILE = "ruby_shop.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# DATABASE
# ============================================================

def db_connect():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db_connect()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT,
            username TEXT,
            phone TEXT,
            product_text TEXT,
            product_link TEXT,
            product_photo TEXT,
            color TEXT,
            size TEXT,
            quantity TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    connection.commit()
    connection.close()


def create_order(data):
    connection = db_connect()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO orders (
            user_id,
            full_name,
            username,
            phone,
            product_text,
            product_link,
            product_photo,
            color,
            size,
            quantity,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("telegram_id"),
        data.get("full_name"),
        data.get("telegram_username"),
        data.get("phone"),
        data.get("product_text"),
        data.get("product_link"),
        data.get("product_photo"),
        data.get("color"),
        data.get("size"),
        data.get("quantity"),
        "Ожидает подтверждения",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))

    order_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return order_id


def get_order(order_id):
    connection = db_connect()

    order = connection.execute(
        "SELECT * FROM orders WHERE id = ?",
        (order_id,)
    ).fetchone()

    connection.close()

    return order


def get_user_orders(user_id):
    connection = db_connect()

    orders = connection.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return orders


def update_order_status(order_id, status):
    connection = db_connect()

    connection.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (status, order_id)
    )

    connection.commit()
    connection.close()


# ============================================================
# STATES
# ============================================================

class Order(StatesGroup):
    product = State()
    color = State()
    size = State()
    quantity = State()
    phone = State()
    confirm = State()


class Question(StatesGroup):
    waiting = State()


class Admin(StatesGroup):
    waiting_new_album = State()


# ============================================================
# ALBUM STORAGE
# ============================================================

album_buffer = {}
album_tasks = {}


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛍️ Оформить заказ"),
                KeyboardButton(text="📦 Мои заказы"),
            ],
            [
                KeyboardButton(text="📋 Условия заказа"),
                KeyboardButton(text="💬 Задать вопрос"),
            ],
            [
                KeyboardButton(text="✈️ Telegram-канал"),
            ],
        ],
        resize_keyboard=True,
    )


def back_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏠 В меню",
        callback_data="back_to_menu"
    )

    return builder.as_markup()


phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="📱 Отправить номер телефона",
                request_contact=True
            )
        ],
        [
            KeyboardButton(
                text="Не отправлять номер телефона"
            )
        ],
    ],
    resize_keyboard=True,
)


def progress(step):
    return " ━ ".join(
        "●" if i < step else "○"
        for i in range(5)
    )


def admin_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📤 Опубликовать товар",
        callback_data="admin_publish"
    )

    builder.button(
        text="❌ Закрыть",
        callback_data="admin_close"
    )

    builder.adjust(1)

    return builder.as_markup()


async def order_button():
    me = await bot.get_me()

    if not me.username:
        raise RuntimeError(
            "У бота не установлен username."
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍️ Заказать",
                    url=f"https://t.me/{me.username}"
                )
            ]
        ]
    )


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "RUBY SHOP\n\n"
        "Здравствуйте. Добро пожаловать в Ruby Shop.\n\n"
        "Онлайн-магазин одежды • Донецк\n\n"
        "Выберите действие ниже.",
        reply_markup=main_keyboard()
    )


# ============================================================
# ADMIN PANEL
# ============================================================

@dp.message(Command("channel"))
async def channel_admin(
    message: Message,
    state: FSMContext
):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("Команда недоступна.")
        return

    await state.clear()

    await message.answer(
        "🔐 УПРАВЛЕНИЕ RUBY SHOP\n\n"
        "📤 Опубликовать товар\n\n"
        "Нажми кнопку и отправь альбом "
        "из 2–10 фотографий.\n\n"
        "Описание товара добавь в подпись "
        "к первой фотографии.",
        reply_markup=admin_keyboard()
    )


@dp.callback_query(F.data == "admin_close")
async def admin_close(
    callback: CallbackQuery,
    state: FSMContext
):
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer(
            "Недостаточно прав.",
            show_alert=True
        )
        return

    await state.clear()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "🔐 Управление каналом закрыто.",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_publish")
async def admin_publish(
    callback: CallbackQuery,
    state: FSMContext
):
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer(
            "Недостаточно прав.",
            show_alert=True
        )
        return

    await state.clear()
    await state.set_state(Admin.waiting_new_album)

    await callback.message.answer(
        "📤 ПУБЛИКАЦИЯ ТОВАРА\n\n"
        "Отправь сюда ОДИН альбом "
        "из 2–10 фотографий.\n\n"
        "Описание товара напиши в подписи "
        "к первой фотографии.\n\n"
        "Например:\n\n"
        "NIKE TECH FLEECE\n"
        "Размеры: S–XL\n"
        "Цвет: Black\n"
        "Качество: Premium\n\n"
        "После этого бот создаст новый альбом "
        "в канале и добавит кнопку "
        "«🛍️ Заказать».",
        reply_markup=back_keyboard()
    )

    await callback.answer()


# ============================================================
# ALBUM PUBLISH
# ============================================================

async def publish_album(
    media_group_id,
    state: FSMContext
):
    try:
        await asyncio.sleep(1.5)

        album = album_buffer.get(media_group_id)

        if not album:
            return

        photos = album["photos"]
        caption = album["caption"]

        if len(photos) < 2:
            await bot.send_message(
                ADMIN_CHAT_ID,
                "⚠️ Получено меньше 2 фотографий.\n\n"
                "Отправь товар одним альбомом "
                "из 2–10 фотографий."
            )

            return

        photos = photos[:10]

        media = []

        for index, file_id in enumerate(photos):

            if index == 0 and caption:
                media.append(
                    InputMediaPhoto(
                        media=file_id,
                        caption=caption[:1024]
                    )
                )
            else:
                media.append(
                    InputMediaPhoto(
                        media=file_id
                    )
                )

        sent_messages = await bot.send_media_group(
            chat_id=SHOP_CHANNEL,
            media=media
        )

        # Кнопка добавляется к последнему сообщению
        # созданного альбома.
        await bot.edit_message_reply_markup(
            chat_id=SHOP_CHANNEL,
            message_id=sent_messages[-1].message_id,
            reply_markup=await order_button()
        )

        await bot.send_message(
            ADMIN_CHAT_ID,
            "✅ ТОВАР ОПУБЛИКОВАН\n\n"
            f"📸 Фотографий: {len(photos)}\n\n"
            f"📢 Альбом опубликован в {SHOP_CHANNEL}.\n\n"
            "🛍️ Кнопка «Заказать» добавлена.",
            reply_markup=main_keyboard()
        )

        await state.clear()

    except asyncio.CancelledError:
        return

    except Exception as error:
        logging.exception(
            "Ошибка публикации альбома"
        )

        await bot.send_message(
            ADMIN_CHAT_ID,
            "❌ Не удалось опубликовать альбом.\n\n"
            "Проверь, что бот является администратором "
            "канала и имеет право публиковать сообщения.\n\n"
            f"Ошибка:\n{error}"
        )

    finally:
        album_buffer.pop(
            media_group_id,
            None
        )

        album_tasks.pop(
            media_group_id,
            None
        )


# ============================================================
# RECEIVE ALBUM
# ============================================================

@dp.message(
    Admin.waiting_new_album,
    F.media_group_id
)
async def receive_album(
    message: Message,
    state: FSMContext
):
    if message.from_user.id != ADMIN_CHAT_ID:
        return

    if not message.photo:
        return

    group_id = message.media_group_id

    album = album_buffer.setdefault(
        group_id,
        {
            "photos": [],
            "caption": None
        }
    )

    album["photos"].append(
        message.photo[-1].file_id
    )

    if message.caption:
        album["caption"] = message.caption

    old_task = album_tasks.get(group_id)

    if old_task:
        old_task.cancel()

    album_tasks[group_id] = asyncio.create_task(
        publish_album(
            group_id,
            state
        )
    )


@dp.message(Admin.waiting_new_album)
async def admin_album_fallback(
    message: Message,
    state: FSMContext
):
    if message.from_user.id != ADMIN_CHAT_ID:
        return

    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_keyboard()
        )

        return

    await message.answer(
        "⚠️ Отправь именно альбом "
        "из 2–10 фотографий.\n\n"
        "Описание товара добавь в подпись "
        "к первой фотографии.",
        reply_markup=back_keyboard()
    )


# ============================================================
# CONDITIONS
# ============================================================

@dp.message(F.text == "📋 Условия заказа")
async def conditions(message: Message):
    await message.answer(
        "📋 УСЛОВИЯ ЗАКАЗА\n\n"
        "🛍️ Выбор товара\n"
        "Выбираете товар и оформляете заказ "
        "прямо в боте Ruby Shop.\n\n"
        "🔗 Ссылка на товар\n"
        "Можно переслать сообщение с товаром "
        "из нашего Telegram-канала или отправить ссылку.\n\n"
        "💳 Предоплата\n"
        "Для подтверждения заказа вносится "
        "предоплата — 50%.\n\n"
        "📦 Доставка\n"
        "Ориентировочно 5–10 дней.\n\n"
        "🤍 Получение\n"
        "После поступления товара в Донецк "
        "оплачиваются оставшиеся 50%.\n\n"
        "С любовью, Ruby Shop 💋",
        reply_markup=main_keyboard()
    )


# ============================================================
# CHANNEL
# ============================================================

@dp.message(F.text == "✈️ Telegram-канал")
async def channel(message: Message):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✈️ Открыть канал",
        url=SHOP_CHANNEL_URL
    )

    await message.answer(
        "✈️ TELEGRAM-КАНАЛ RUBY SHOP\n\n"
        "Актуальный ассортимент, новинки "
        "и новые дропы.",
        reply_markup=builder.as_markup()
    )


# ============================================================
# ORDER
# ============================================================

@dp.message(F.text == "🛍️ Оформить заказ")
async def start_order(
    message: Message,
    state: FSMContext
):
    await state.clear()
    await state.set_state(Order.product)

    await message.answer(
        "🛍️ ОФОРМЛЕНИЕ ЗАКАЗА\n\n"
        f"{progress(1)}\n\n"
        "Шаг 1 из 5\n\n"
        "👕 Отправьте товар, который хотите заказать.\n\n"
        "Можно переслать сообщение с товаром "
        "из нашего канала или отправить ссылку.",
        reply_markup=back_keyboard()
    )


@dp.message(Order.product)
async def get_product(
    message: Message,
    state: FSMContext
):
    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_keyboard()
        )

        return

    product_photo = None
    product_text = None
    product_link = None

    if message.photo:

        product_photo = message.photo[-1].file_id

        if message.caption:
            product_text = message.caption.strip()

        try:
            if (
                message.forward_origin
                and getattr(
                    message.forward_origin.chat,
                    "username",
                    None
                )
            ):
                product_link = (
                    "https://t.me/"
                    f"{message.forward_origin.chat.username}/"
                    f"{message.forward_origin.message_id}"
                )

        except Exception:
            pass

    elif message.text:

        product_text = message.text.strip()

        if (
            "https://" in product_text
            or "http://" in product_text
        ):
            product_link = product_text

    else:

        await message.answer(
            "Пожалуйста, перешлите товар "
            "или отправьте ссылку.",
            reply_markup=back_keyboard()
        )

        return

    await state.update_data(
        product_photo=product_photo,
        product_text=product_text,
        product_link=product_link
    )

    await state.set_state(Order.color)

    await message.answer(
        "🎨 ЦВЕТ\n\n"
        f"{progress(2)}\n\n"
        "Шаг 2 из 5\n\n"
        "Укажите цвет товара.",
        reply_markup=back_keyboard()
    )


@dp.message(Order.color)
async def get_color(
    message: Message,
    state: FSMContext
):
    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_keyboard()
        )

        return

    await state.update_data(
        color=message.text.strip()
    )

    await state.set_state(Order.size)

    await message.answer(
        "📏 РАЗМЕР\n\n"
        f"{progress(3)}\n\n"
        "Шаг 3 из 5\n\n"
        "Укажите размер товара.",
        reply_markup=back_keyboard()
    )


@dp.message(Order.size)
async def get_size(
    message: Message,
    state: FSMContext
):
    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_keyboard()
        )

        return

    await state.update_data(
        size=message.text.strip()
    )

    await state.set_state(Order.quantity)

    await message.answer(
        "🔢 КОЛИЧЕСТВО\n\n"
        f"{progress(4)}\n\n"
        "Шаг 4 из 5\n\n"
        "Укажите количество товара.",
        reply_markup=back_keyboard()
    )


@dp.message(Order.quantity)
async def get_quantity(
    message: Message,
    state: FSMContext
):
    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_keyboard()
        )

        return

    quantity = message.text.strip()

    if not quantity.isdigit() or int(quantity) <= 0:
        await message.answer(
            "⚠️ Укажите количество цифрами.\n\n"
            "Например: 1 или 2.",
            reply_markup=back_keyboard()
        )

        return

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "username не установлен"
    )

    await state.update_data(
        quantity=quantity,
        full_name=user.full_name,
        telegram_username=username,
        telegram_id=user.id
    )

    await state.set_state(Order.phone)

    await message.answer(
        "📱 КОНТАКТНЫЕ ДАННЫЕ\n\n"
        f"{progress(5)}\n\n"
        "Шаг 5 из 5\n\n"
        "При желании отправьте номер телефона "
        "или продолжите без него.",
        reply_markup=phone_keyboard
    )


# ============================================================
# PHONE
# ============================================================

@dp.message(Order.phone, F.contact)
async def get_phone(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        phone=message.contact.phone_number
    )

    await show_summary(
        message,
        state
    )


@dp.message(
    Order.phone,
    F.text == "Не отправлять номер телефона"
)
async def skip_phone(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        phone="Не предоставлен"
    )

    await show_summary(
        message,
        state
    )


# ============================================================
# ORDER SUMMARY
# ============================================================

async def show_summary(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    product_text = (
        data.get("product_text")
        or "Описание отсутствует"
    )

    summary = (
        "🛍️ ПРОВЕРЬТЕ ЗАКАЗ\n\n"
        "━━━━━━━━━━━━━━\n\n"
        f"👕 Товар\n{product_text}\n\n"
        f"🎨 Цвет\n{data.get('color')}\n\n"
        f"📏 Размер\n{data.get('size')}\n\n"
        f"📦 Количество\n"
        f"{data.get('quantity')} шт.\n\n"
        f"📱 Telegram\n"
        f"{data.get('telegram_username')}\n\n"
        f"☎️ Телефон\n"
        f"{data.get('phone')}\n\n"
        "━━━━━━━━━━━━━━\n\n"
        "💳 Оплата\n"
        "50% — предоплата\n"
        "50% — после получения\n\n"
        "🚚 Доставка\n"
        "ориентировочно 5–10 дней\n\n"
        "Всё верно?"
    )

    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Подтвердить заказ",
        callback_data="confirm_order"
    )

    builder.button(
        text="❌ Отменить",
        callback_data="cancel_order"
    )

    builder.adjust(1)

    await state.set_state(Order.confirm)

    await message.answer(
        summary,
        reply_markup=builder.as_markup()
    )


# ============================================================
# BACK TO MENU
# ============================================================

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# CONFIRM ORDER
# ============================================================

@dp.callback_query(
    Order.confirm,
    F.data == "confirm_order"
)
async def confirm_order(
    callback: CallbackQuery,
    state: FSMContext
):
    data = await state.get_data()

    order_id = create_order(data)

    product_photo = data.get(
        "product_photo"
    )

    product_text = (
        data.get("product_text")
        or "Описание отсутствует"
    )

    product_link = data.get(
        "product_link"
    )

    admin_text = (
        "🔴 НОВЫЙ ЗАКАЗ — RUBY SHOP\n\n"
        f"🆔 Заказ №{order_id}\n\n"
        "👤 КЛИЕНТ\n"
        f"Имя: {data.get('full_name')}\n"
        f"Telegram: {data.get('telegram_username')}\n"
        f"Telegram ID: {data.get('telegram_id')}\n"
        f"Телефон: {data.get('phone')}\n\n"
        "🛍️ ТОВАР\n"
        f"{product_text}\n\n"
        f"🎨 Цвет: {data.get('color')}\n"
        f"📏 Размер: {data.get('size')}\n"
        f"📦 Количество: {data.get('quantity')}\n\n"
        "💳 ОПЛАТА\n"
        "50% — предоплата\n"
        "50% — после получения\n\n"
        "🟡 Статус: ожидает подтверждения"
    )

    if product_link:
        admin_text += (
            "\n\n🔗 Ссылка на товар:\n"
            f"{product_link}"
        )

    status_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=(
                        f"status_confirmed:{order_id}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚚 Товар в пути",
                    callback_data=(
                        f"status_delivery:{order_id}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Товар в Донецке",
                    callback_data=(
                        f"status_donetsk:{order_id}"
                    )
                ],
            ],
            [
                InlineKeyboardButton(
                    text="🤍 Заказ получен",
                    callback_data=(
                        f"status_received:{order_id}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить заказ",
                    callback_data=(
                        f"status_cancelled:{order_id}"
                    )
                )
            ],
        ]
    )

    if product_photo:
        await bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=product_photo,
            caption=admin_text,
            reply_markup=status_keyboard
        )
    else:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text,
            reply_markup=status_keyboard
        )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "✅ ЗАКАЗ ОФОРМЛЕН\n\n"
        f"Ваш заказ №{order_id} принят.\n\n"
        "🟡 Статус\n"
        "Ожидает подтверждения\n\n"
        "Мы проверим наличие товара "
        "и свяжемся с вами.",
        reply_markup=main_keyboard()
    )

    await state.clear()
    await callback.answer()


# ============================================================
# CANCEL ORDER
# ============================================================

@dp.callback_query(
    Order.confirm,
    F.data == "cancel_order"
)
async def cancel_order(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "❌ Заказ отменён.\n\n"
        "Если захотите оформить его снова, "
        "нажмите «🛍️ Оформить заказ».",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# MY ORDERS
# ============================================================

@dp.message(F.text == "📦 Мои заказы")
async def my_orders(message: Message):
    orders = get_user_orders(
        message.from_user.id
    )

    if not orders:
        await message.answer(
            "📦 МОИ ЗАКАЗЫ\n\n"
            "У вас пока нет оформленных заказов.",
            reply_markup=main_keyboard()
        )
        return

    text = "📦 МОИ ЗАКАЗЫ\n\n"

    for order in orders:

        product = (
            order["product_text"]
            or "Товар"
        )

        if len(product) > 80:
            product = product[:80] + "..."

        text += (
            f"🛍️ Заказ №{order['id']}\n"
            f"Товар: {product}\n"
            f"Размер: {order['size']}\n"
            f"Количество: {order['quantity']}\n"
            f"Статус: {order['status']}\n"
            f"Дата: {order['created_at']}\n\n"
        )

    await message.answer(
        text,
        reply_markup=main_keyboard()
    )


# ============================================================
# STATUS CHANGES
# ============================================================

async def change_status(
    callback,
    order_id,
    status,
    client_status,
    message_text
):
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer(
            "Недостаточно прав.",
            show_alert=True
        )
        return

    order = get_order(order_id)

    if not order:
        await callback.answer(
            "Заказ не найден.",
            show_alert=True
        )
        return

    update_order_status(
        order_id,
        status
    )

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=(
                "🔴 RUBY SHOP\n\n"
                f"📦 Заказ №{order_id}\n\n"
                f"{message_text}\n\n"
                f"Текущий статус: {client_status}"
            )
        )

    except Exception as error:
        logging.error(
            "Не удалось уведомить клиента: %s",
            error
        )

    await callback.answer(
        f"Статус изменён: {client_status}"
    )


@dp.callback_query(
    F.data.startswith("status_confirmed:")
)
async def status_confirmed(
    callback: CallbackQuery
):
    order_id = int(
        callback.data.split(":")[1]
    )

    await change_status(
        callback,
        order_id,
        "Подтверждён",
        "Подтверждён",
        "Ваш заказ подтверждён. "
        "Мы запускаем его в работу."
    )


@dp.callback_query(
    F.data.startswith("status_delivery:")
)
async def status_delivery(
    callback: CallbackQuery
):
    order_id = int(
        callback.data.split(":")[1]
    )

    await change_status(
        callback,
        order_id,
        "Товар в пути",
        "Товар в пути",
        "Ваш товар уже в пути к нам."
    )


@dp.callback_query(
    F.data.startswith("status_donetsk:")
)
async def status_donetsk(
    callback: CallbackQuery
):
    order_id = int(
        callback.data.split(":")[1]
    )

    await change_status(
        callback,
        order_id,
        "Товар в Донецке",
        "Товар в Донецке",
        "Ваш товар уже поступил в Донецк."
    )


@dp.callback_query(
    F.data.startswith("status_received:")
)
async def status_received(
    callback: CallbackQuery
):
    order_id = int(
        callback.data.split(":")[1]
    )

    await change_status(
        callback,
        order_id,
        "Получен",
        "Заказ получен",
        "Ваш заказ отмечен как полученный."
    )


@dp.callback_query(
    F.data.startswith("status_cancelled:")
)
async def status_cancelled(
    callback: CallbackQuery
):
    order_id = int(
        callback.data.split(":")[1]
    )

    await change_status(
        callback,
        order_id,
        "Отменён",
        "Заказ отменён",
        "Ваш заказ был отменён."
    )


# ============================================================
# QUESTIONS
# ============================================================

@dp.message(F.text == "💬 Задать вопрос")
async def ask_question(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        Question.waiting
    )

    await message.answer(
        "💬 ВОПРОС\n\n"
        "Напишите ваш вопрос одним сообщением.\n\n"
        "Мы передадим его менеджеру Ruby Shop.",
        reply_markup=main_keyboard()
    )


@dp.message(Question.waiting)
async def receive_question(
    message: Message,
    state: FSMContext
):
    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_keyboard()
        )

        return

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "username не установлен"
    )

    await bot.send_message(
        ADMIN_CHAT_ID,
        "💬 НОВЫЙ ВОПРОС — RUBY SHOP\n\n"
        f"Имя: {user.full_name}\n"
        f"Telegram: {username}\n"
        f"Telegram ID: {user.id}\n\n"
        f"Вопрос:\n{message.text}"
    )

    await message.answer(
        "✅ Вопрос отправлен.\n\n"
        "Мы свяжемся с вами, как только сможем.",
        reply_markup=main_keyboard()
    )

    await state.clear()


# ============================================================
# MAIN
# ============================================================

async def main():
    init_db()

    logging.info(
        "Ruby Shop bot запускается..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
