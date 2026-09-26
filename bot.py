import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Telegram-канал Ruby Shop
SHOP_CHANNEL_URL = "https://t.me/ruby_shop_dn"

DB_FILE = "ruby_shop.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def db_connect():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db_connect()
    cursor = connection.cursor()

    cursor.execute("""
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
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM orders WHERE id = ?",
        (order_id,)
    )

    order = cursor.fetchone()

    connection.close()

    return order


def get_user_orders(user_id):
    connection = db_connect()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,))

    orders = cursor.fetchall()

    connection.close()

    return orders


def update_order_status(order_id, status):
    connection = db_connect()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (status, order_id))

    connection.commit()
    connection.close()


# =========================================================
# СОСТОЯНИЯ
# =========================================================

class Order(StatesGroup):
    product = State()
    color = State()
    size = State()
    quantity = State()
    phone = State()
    confirm = State()
    editing = State()


class Question(StatesGroup):
    waiting = State()


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

def get_main_keyboard():

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
        resize_keyboard=True
    )


# =========================================================
# КНОПКА В МЕНЮ
# =========================================================

def back_menu_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🏠 В меню",
        callback_data="back_to_menu"
    )

    return builder.as_markup()


# =========================================================
# ТЕЛЕФОН
# =========================================================

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
    resize_keyboard=True
)


# =========================================================
# ПРОГРЕСС
# =========================================================

def progress(step):

    symbols = []

    for i in range(5):
        if i < step:
            symbols.append("●")
        else:
            symbols.append("○")

    return " ━ ".join(symbols)


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    await state.clear()

    text = (
        "RUBY SHOP\n\n"
        "Здравствуйте. Добро пожаловать в Ruby Shop.\n\n"
        "Онлайн-магазин одежды • Донецк\n\n"
        "Выберите действие ниже."
    )

    await message.answer(
        text,
        reply_markup=get_main_keyboard()
    )


# =========================================================
# УСЛОВИЯ
# =========================================================

@dp.message(F.text == "📋 Условия заказа")
async def conditions(message: Message):

    text = (
        "📋 УСЛОВИЯ ЗАКАЗА\n\n"

        "🛍️ Выбор товара\n"
        "Выбираете понравившийся товар и оформляете заказ "
        "прямо в боте Ruby Shop. Бот последовательно запросит "
        "необходимые данные и сформирует ваш заказ.\n\n"

        "🔗 Ссылка на товар\n"
        "При оформлении заказа можно переслать сообщение "
        "с товаром из нашего Telegram-канала или отправить "
        "ссылку на конкретный товар.\n\n"

        "💳 Предоплата\n"
        "Для подтверждения заказа вносится предоплата — "
        "50% от стоимости товара. После подтверждения "
        "мы запускаем заказ в работу.\n\n"

        "📦 Доставка\n"
        "Товар поступает к нам в Донецк в течение 5–10 дней.\n"
        "Срок является ориентировочным и может немного изменяться.\n\n"

        "🤍 Получение товара\n"
        "После поступления товара в Донецк вы получаете заказ "
        "и оплачиваете оставшиеся 50% стоимости.\n\n"

        "Весь процесс — от выбора товара до получения заказа — "
        "проходит через Ruby Shop.\n\n"

        "С любовью, Ruby Shop 💋\n"
        "Онлайн-магазин • Донецк"
    )

    await message.answer(
        text,
        reply_markup=get_main_keyboard()
    )


# =========================================================
# TELEGRAM-КАНАЛ
# =========================================================

@dp.message(F.text == "✈️ Telegram-канал")
async def telegram_channel(message: Message):

    builder = InlineKeyboardBuilder()

    builder.button(
        text="✈️ Открыть канал",
        url=SHOP_CHANNEL_URL
    )

    await message.answer(
        "✈️ TELEGRAM-КАНАЛ RUBY SHOP\n\n"
        "Здесь можно посмотреть актуальный ассортимент, "
        "новинки и новые дропы.",
        reply_markup=builder.as_markup()
    )


# =========================================================
# НАЧАЛО ЗАКАЗА
# =========================================================

@dp.message(F.text == "🛍️ Оформить заказ")
async def start_order(message: Message, state: FSMContext):

    await state.clear()
    await state.set_state(Order.product)

    await message.answer(
        "🛍️ ОФОРМЛЕНИЕ ЗАКАЗА\n\n"
        f"{progress(1)}\n\n"
        "Шаг 1 из 5\n\n"
        "👕 Отправьте товар, который хотите заказать.\n\n"
        "Можно переслать сообщение с товаром из "
        "нашего Telegram-канала или отправить ссылку.",
        reply_markup=back_menu_keyboard()
    )


# =========================================================
# ТОВАР
# =========================================================

@dp.message(Order.product)
async def get_product(message: Message, state: FSMContext):

    if message.text == "🏠 В меню":

        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=get_main_keyboard()
        )

        return

    product_photo = None
    product_text = None
    product_link = None

    if message.photo:

        product_photo = message.photo[-1].file_id

        if message.caption:
            product_text = message.caption.strip()

        if message.forward_origin:

            origin = message.forward_origin

            if hasattr(origin, "chat") and hasattr(origin, "message_id"):

                chat = origin.chat

                if getattr(chat, "username", None):

                    product_link = (
                        f"https://t.me/"
                        f"{chat.username}/"
                        f"{origin.message_id}"
                    )

    elif message.text:

        product_text = message.text.strip()

        if "https://" in product_text or "http://" in product_text:
            product_link = product_text

    else:

        await message.answer(
            "Пожалуйста, пересылайте пост с товаром "
            "из нашего Telegram-канала или отправьте ссылку.",
            reply_markup=back_menu_keyboard()
        )

        return

    await state.update_data(
        product_photo=product_photo,
        product_text=product_text,
        product_link=product_link,
    )

    await state.set_state(Order.color)

    await message.answer(
        "🎨 ЦВЕТ\n\n"
        f"{progress(2)}\n\n"
        "Шаг 2 из 5\n\n"
        "Укажите цвет товара.",
        reply_markup=back_menu_keyboard()
    )


# =========================================================
# ЦВЕТ
# =========================================================

@dp.message(Order.color)
async def get_color(message: Message, state: FSMContext):

    if message.text == "🏠 В меню":

        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=get_main_keyboard()
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
        reply_markup=back_menu_keyboard()
    )


# =========================================================
# РАЗМЕР
# =========================================================

@dp.message(Order.size)
async def get_size(message: Message, state: FSMContext):

    if message.text == "🏠 В меню":

        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=get_main_keyboard()
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
        reply_markup=back_menu_keyboard()
    )


# =========================================================
# КОЛИЧЕСТВО
# =========================================================

@dp.message(Order.quantity)
async def get_quantity(message: Message, state: FSMContext):

    if message.text == "🏠 В меню":

        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=get_main_keyboard()
        )

        return

    quantity = message.text.strip()

    if not quantity.isdigit() or int(quantity) <= 0:

        await message.answer(
            "⚠️ Укажите количество цифрами.\n\n"
            "Например: 1 или 2.",
            reply_markup=back_menu_keyboard()
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
        telegram_id=user.id,
    )

    await state.set_state(Order.phone)

    await message.answer(
        "📱 КОНТАКТНЫЕ ДАННЫЕ\n\n"
        f"{progress(5)}\n\n"
        "Шаг 5 из 5\n\n"
        "При желании отправьте номер телефона для связи "
        "по заказу или продолжите без него.",
        reply_markup=phone_keyboard
    )


# =========================================================
# ТЕЛЕФОН
# =========================================================

@dp.message(Order.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):

    await state.update_data(
        phone=message.contact.phone_number
    )

    await show_summary(message, state)


@dp.message(
    Order.phone,
    F.text == "Не отправлять номер телефона"
)
async def skip_phone(message: Message, state: FSMContext):

    await state.update_data(
        phone="Не предоставлен"
    )

    await show_summary(message, state)


# =========================================================
# СВОДКА
# =========================================================

async def show_summary(message: Message, state: FSMContext):

    data = await state.get_data()

    product_text = (
        data.get("product_text")
        or "Описание отсутствует"
    )

    summary = (
        "🛍️ ПРОВЕРЬТЕ ЗАКАЗ\n\n"

        "━━━━━━━━━━━━━━\n\n"

        f"👕 Товар\n"
        f"{product_text}\n\n"

        f"🎨 Цвет\n"
        f"{data.get('color')}\n\n"

        f"📏 Размер\n"
        f"{data.get('size')}\n\n"

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
        text="✏️ Изменить данные",
        callback_data="edit_order"
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


# =========================================================
# В МЕНЮ
# =========================================================

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=get_main_keyboard()
    )

    await callback.answer()


# =========================================================
# ПОДТВЕРЖДЕНИЕ
# =========================================================

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

    product_photo = data.get("product_photo")
    product_text = (
        data.get("product_text")
        or "Описание отсутствует"
    )
    product_link = data.get("product_link")

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
                    callback_data=f"status_confirmed:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚚 Товар в пути",
                    callback_data=f"status_delivery:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Товар в Донецке",
                    callback_data=f"status_donetsk:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🤍 Заказ получен",
                    callback_data=f"status_received:{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить заказ",
                    callback_data=f"status_cancelled:{order_id}"
                ),
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
        "Мы проверим наличие товара и свяжемся "
        "с вами для дальнейшего оформления.\n\n"
        "Спасибо, что выбрали Ruby Shop.",
        reply_markup=get_main_keyboard()
    )

    await state.clear()
    await callback.answer()


# =========================================================
# ОТМЕНА
# =========================================================

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
        reply_markup=get_main_keyboard()
    )

    await callback.answer()


# =========================================================
# МОИ ЗАКАЗЫ
# =========================================================

@dp.message(F.text == "📦 Мои заказы")
async def my_orders(message: Message):

    orders = get_user_orders(
        message.from_user.id
    )

    if not orders:

        await message.answer(
            "📦 МОИ ЗАКАЗЫ\n\n"
            "У вас пока нет оформленных заказов.",
            reply_markup=get_main_keyboard()
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
        reply_markup=get_main_keyboard()
    )


# =========================================================
# СТАТУСЫ — АДМИН
# =========================================================

async def change_status(
    callback: CallbackQuery,
    order_id: int,
    status: str,
    client_status: str,
    message_text: str
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
            f"Не удалось уведомить клиента: {error}"
        )

    await callback.answer(
        f"Статус изменён: {client_status}"
    )


@dp.callback_query(
    F.data.startswith("status_confirmed:")
)
async def status_confirmed(callback: CallbackQuery):

    order_id = int(
        callback.data.split(":")[1]
    )

    await change_status(
        callback,
        order_id,
        "Подтверждён",
        "Подтверждён",
        "Ваш заказ подтверждён. Мы запускаем его в работу."
