import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ============================================================
# SETTINGS
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

SHOP_CHANNEL_URL = "https://t.me/ruby_shop_dn"
SHOP_CHANNEL = "@ruby_shop_dn"

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
    waiting_existing_post = State()
    waiting_new_post = State()


# ============================================================
# MAIN MENU
# ============================================================

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛍️ Оформить заказ"),
                KeyboardButton(text="📦 Мои заказы")
            ],
            [
                KeyboardButton(text="📋 Условия заказа"),
                KeyboardButton(text="💬 Задать вопрос")
            ],
            [
                KeyboardButton(text="✈️ Telegram-канал")
            ],
        ],
        resize_keyboard=True
    )


def back_menu_keyboard():
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
    resize_keyboard=True
)


def progress(step):
    symbols = []

    for i in range(5):
        if i < step:
            symbols.append("●")
        else:
            symbols.append("○")

    return " ━ ".join(symbols)


# ============================================================
# ADMIN KEYBOARD
# ============================================================

def get_admin_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="➕ Добавить кнопку к посту",
        callback_data="admin_add_button"
    )

    builder.button(
        text="📤 Опубликовать новый товар",
        callback_data="admin_publish"
    )

    builder.button(
        text="❌ Закрыть",
        callback_data="admin_close"
    )

    builder.adjust(1)

    return builder.as_markup()


# ============================================================
# ORDER BUTTON
# ============================================================

async def get_order_button():
    me = await bot.get_me()

    if not me.username:
        raise RuntimeError(
            "У бота не установлен username."
        )

    bot_link = f"https://t.me/{me.username}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍️ Заказать",
                    url=bot_link
                )
            ]
        ]
    )


# ============================================================
# START
# ============================================================

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


# ============================================================
# ADMIN CHANNEL PANEL
# ============================================================

@dp.message(Command("channel"))
async def admin_channel(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer(
            "Команда недоступна."
        )
        return

    await state.clear()

    await message.answer(
        "🔐 УПРАВЛЕНИЕ RUBY SHOP\n\n"
        "Здесь ты можешь управлять товарами в Telegram-канале.\n\n"
        "➕ Добавить кнопку к посту — "
        "перешли сюда уже существующий пост из канала.\n\n"
        "📤 Опубликовать новый товар — "
        "отправь фото, текст или другое сообщение, "
        "и бот разместит его в канале с кнопкой.",
        reply_markup=get_admin_keyboard()
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
        reply_markup=get_main_keyboard()
    )

    await callback.answer()


# ============================================================
# ADMIN — ADD BUTTON TO EXISTING POST
# ============================================================

@dp.callback_query(F.data == "admin_add_button")
async def admin_add_button(
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
    await state.set_state(Admin.waiting_existing_post)

    await callback.message.answer(
        "➕ ДОБАВЛЕНИЕ КНОПКИ\n\n"
        "Теперь просто пересылай сюда пост "
        "из канала Ruby Shop.\n\n"
        "Бот определит оригинальный пост "
        "и добавит под ним кнопку:\n\n"
        "🛍️ Заказать\n\n"
        "Важно: пересылай именно пост из канала, "
        "а не скриншот.",
        reply_markup=back_menu_keyboard()
    )

    await callback.answer()


@dp.message(Admin.waiting_existing_post)
async def process_existing_post(
    message: Message,
    state: FSMContext
):
    if message.from_user.id != ADMIN_CHAT_ID:
        return

    # --------------------------------------------------------
    # Возврат в меню
    # --------------------------------------------------------

    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=get_main_keyboard()
        )

        return

    # --------------------------------------------------------
    # Вариант 1: пользователь переслал пост
    # --------------------------------------------------------

    if message.forward_origin:

        origin = message.forward_origin

        try:
            origin_chat = origin.chat
            origin_message_id = origin.message_id
        except AttributeError:
            await message.answer(
                "❌ Не удалось определить оригинальный пост.\n\n"
                "Попробуй переслать пост из канала ещё раз."
            )
            return

        try:
            channel_chat = await bot.get_chat(
                SHOP_CHANNEL
            )

            # Проверяем, что пост действительно из нашего канала
            if origin_chat.id != channel_chat.id:
                await message.answer(
                    "❌ Этот пост не из канала Ruby Shop.\n\n"
                    "Перешли пост именно из:\n"
                    "@ruby_shop_dn"
                )
                return

            keyboard = await get_order_button()

            await bot.edit_message_reply_markup(
                chat_id=channel_chat.id,
                message_id=origin_message_id,
                reply_markup=keyboard
            )

            await state.clear()

            await message.answer(
                "✅ ГОТОВО!\n\n"
                f"К посту №{origin_message_id} "
                "добавлена кнопка:\n\n"
                "🛍️ Заказать\n\n"
                "Теперь кнопку увидят подписчики канала.",
                reply_markup=get_main_keyboard()
            )

            return

        except Exception as error:
            logging.exception(
                "Ошибка добавления кнопки к существующему посту"
            )

            await message.answer(
                "❌ Не удалось изменить пост.\n\n"
                "Проверь, что бот является администратором "
                "канала Ruby Shop и имеет право "
                "«Изменение сообщений».\n\n"
                f"Техническая ошибка:\n{error}"
            )

            return

    # --------------------------------------------------------
    # Вариант 2: пользователь отправил ссылку
    # --------------------------------------------------------

    if message.text and message.text.startswith(
        "https://t.me/"
    ):

        parsed = parse_channel_post_link(
            message.text
        )

        if not parsed:
            await message.answer(
                "❌ Не удалось распознать ссылку.\n\n"
                "Пример:\n"
                "https://t.me/ruby_shop_dn/255"
            )
            return

        channel_username, message_id = parsed

        if channel_username.lower() != "@ruby_shop_dn":
            await message.answer(
                "❌ Эта функция работает только "
                "с каналом Ruby Shop."
            )
            return

        try:
            keyboard = await get_order_button()

            await bot.edit_message_reply_markup(
                chat_id=SHOP_CHANNEL,
                message_id=message_id,
                reply_markup=keyboard
            )

            await state.clear()

            await message.answer(
                "✅ ГОТОВО!\n\n"
                f"К посту №{message_id} "
                "добавлена кнопка:\n\n"
                "🛍️ Заказать",
                reply_markup=get_main_keyboard()
            )

        except Exception as error:
            logging.exception(
                "Ошибка изменения поста по ссылке"
            )

            await message.answer(
                "❌ Не удалось изменить пост.\n\n"
                "Проверь права бота администратора "
                "в канале.\n\n"
                f"Техническая ошибка:\n{error}"
            )

        return

    # --------------------------------------------------------
    # Всё остальное
    # --------------------------------------------------------

    await message.answer(
        "⚠️ Я ожидаю пост из канала.\n\n"
        "Перешли сюда готовый пост из "
        "Ruby Shop или отправь ссылку на него.",
        reply_markup=back_menu_keyboard()
    )


# ============================================================
# ADMIN — PUBLISH NEW POST
# ============================================================

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
    await state.set_state(Admin.waiting_new_post)

    await callback.message.answer(
        "📤 ПУБЛИКАЦИЯ НОВОГО ТОВАРА\n\n"
        "Теперь отправь сюда сообщение, "
        "которое нужно разместить в канале.\n\n"
        "Можно отправить:\n"
        "• фото + описание\n"
        "• обычный текст\n"
        "• видео\n"
        "• документ\n"
        "• другое поддерживаемое сообщение\n\n"
        "Бот скопирует его в канал "
        "и автоматически добавит кнопку:\n\n"
        "🛍️ Заказать",
        reply_markup=back_menu_keyboard()
    )

    await callback.answer()


@dp.message(Admin.waiting_new_post)
async def publish_new_post(
    message: Message,
    state: FSMContext
):
    if message.from_user.id != ADMIN_CHAT_ID:
        return

    if message.text == "🏠 В меню":
        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=get_main_keyboard()
        )

        return

    try:
        keyboard = await get_order_button()

        # Копируем абсолютно любой тип сообщения,
        # который Telegram позволяет копировать.
        result = await bot.copy_message(
            chat_id=SHOP_CHANNEL,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=keyboard
        )

        await state.clear()

        await message.answer(
            "✅ ТОВАР ОПУБЛИКОВАН\n\n"
            "Пост отправлен в канал Ruby Shop.\n\n"
            "🛍️ Кнопка «Заказать» уже добавлена.",
            reply_markup=get_main_keyboard()
        )

        logging.info(
            f"Новый пост опубликован в канале. "
            f"Message ID: {result.message_id}"
        )

    except Exception as error:
        logging.exception(
            "Ошибка публикации нового поста"
        )

        await message.answer(
            "❌ Не удалось опубликовать пост.\n\n"
            "Проверь, что бот является администратором "
            "канала и имеет право публиковать сообщения.\n\n"
            f"Техническая ошибка:\n{error}"
        )


# ============================================================
# CONDITIONS
# ============================================================

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


# ============================================================
# TELEGRAM CHANNEL
# ============================================================

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


# ============================================================
# ORDER — START
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
        "Можно переслать сообщение с товаром из "
        "нашего Telegram-канала или отправить ссылку.",
        reply_markup=back_menu_keyboard()
    )


# ============================================================
# ORDER — PRODUCT
# ============================================================

@dp.message(Order.product)
async def get_product(
    message: Message,
    state: FSMContext
):
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

    # Фото
    if message.photo:

        product_photo = message.photo[-1].file_id

        if message.caption:
            product_text = message.caption.strip()

        if message.forward_origin:

            origin = message.forward_origin

            try:
                chat = origin.chat
                message_id = origin.message_id

                if getattr(chat, "username", None):
                    product_link = (
                        f"https://t.me/"
                        f"{chat.username}/"
                        f"{message_id}"
                    )

            except Exception:
                pass

    # Текст
    elif message.text:

        product_text = message.text.strip()

        if (
            "https://" in product_text
            or "http://" in product_text
        ):
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
        product_link=product_link
    )

    await state.set_state(Order.color)

    await message.answer(
        "🎨 ЦВЕТ\n\n"
        f"{progress(2)}\n\n"
        "Шаг 2 из 5\n\n"
        "Укажите цвет товара.",
        reply_markup=back_menu_keyboard()
    )


# ============================================================
# ORDER — COLOR
# ============================================================

@dp.message(Order.color)
async def get_color(
    message: Message,
    state: FSMContext
):
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


# ============================================================
# ORDER — SIZE
# ============================================================

@dp.message(Order.size)
async def get_size(
    message: Message,
    state: FSMContext
):
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


# ============================================================
# ORDER — QUANTITY
# ============================================================

@dp.message(Order.quantity)
async def get_quantity(
    message: Message,
    state: FSMContext
):
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
        telegram_id=user.id
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


# ============================================================
# ORDER — PHONE
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
# ORDER — SUMMARY
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
        f"📦 Количество\n{data.get('quantity')} шт.\n\n"
        f"📱 Telegram\n{data.get('telegram_username')}\n\n"
        f"☎️ Телефон\n{data.get('phone')}\n\n"
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
        reply_markup=get_main_keyboard()
    )

    await callback.answer()


# ============================================================
# ORDER — CONFIRM
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
                )
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
        "Мы проверим наличие товара и свяжемся "
        "с вами для дальнейшего оформления.\n\n"
        "Спасибо, что выбрали Ruby Shop.",
        reply_markup=get_main_keyboard()
    )

    await state.clear()

    await callback.answer()


# ============================================================
# ORDER — CANCEL
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
        reply_markup=get_main_keyboard()
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


# ============================================================
# ORDER STATUS
# ============================================================

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
        reply_markup=get_main_keyboard()
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
            reply_markup=get_main_keyboard()
        )

        return

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "username не установлен"
    )

    question_text = (
        "💬 НОВЫЙ ВОПРОС — RUBY SHOP\n\n"
        f"Имя: {user.full_name}\n"
        f"Telegram: {username}\n"
        f"Telegram ID: {user.id}\n\n"
        f"Вопрос:\n{message.text}"
    )

    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=question_text
    )

    await message.answer(
        "✅ Вопрос отправлен.\n\n"
        "Мы свяжемся с вами, как только сможем.",
        reply_markup=get_main_keyboard()
    )

    await state.clear()


# ============================================================
# CHANNEL LINK PARSER
# ============================================================

def parse_channel_post_link(link: str):

    link = link.strip().rstrip("/")

    if not link.startswith("https://t.me/"):
        return None

    parts = link.split("/")

    if len(parts) < 5:
        return None

    username = parts[3]
    message_id = parts[4]

    if not message_id.isdigit():
        return None

    return f"@{username}", int(message_id)


# ============================================================
# FALLBACK: ADMIN SENDS CHANNEL LINK
# ============================================================

@dp.message(F.text.startswith("https://t.me/"))
async def add_order_button_by_link(
    message: Message
):

    if message.from_user.id != ADMIN_CHAT_ID:
        return

    parsed = parse_channel_post_link(
        message.text
    )

    if not parsed:

        await message.answer(
            "❌ Не удалось распознать ссылку.\n\n"
            "Отправьте ссылку такого вида:\n"
            "https://t.me/ruby_shop_dn/255"
        )

        return

    channel_username, message_id = parsed

    if channel_username.lower() != "@ruby_shop_dn":

        await message.answer(
            "❌ Эта функция работает только "
            "с каналом Ruby Shop."
        )

        return

    try:

        keyboard = await get_order_button()

        await bot.edit_message_reply_markup(
            chat_id=SHOP_CHANNEL,
            message_id=message_id,
            reply_markup=keyboard
        )

        await message.answer(
            "✅ ГОТОВО!\n\n"
            f"К посту №{message_id} добавлена кнопка:\n\n"
            "🛍️ Заказать"
        )

    except Exception as error:

        logging.exception(
            "Ошибка добавления кнопки по ссылке"
        )

        await message.answer(
            "❌ Не удалось добавить кнопку.\n\n"
            "Проверьте, что бот является администратором "
            "канала и имеет право «Изменение сообщений».\n\n"
            f"Техническая ошибка:\n{error}"
        )


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
