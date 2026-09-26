import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# СОСТОЯНИЯ
# =========================

class Order(StatesGroup):
    product = State()
    color = State()
    size = State()
    quantity = State()
    phone = State()
    confirm = State()


class Question(StatesGroup):
    waiting = State()


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Оформить заказ")],
        [KeyboardButton(text="Условия заказа")],
        [KeyboardButton(text="Задать вопрос")],
    ],
    resize_keyboard=True,
)


# =========================
# ТЕЛЕФОН
# =========================

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="Отправить номер телефона",
                request_contact=True
            )
        ],
        [
            KeyboardButton(text="Не отправлять номер телефона")
        ],
    ],
    resize_keyboard=True,
)


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "RUBY SHOP\n\n"
        "Здравствуйте. Добро пожаловать в Ruby Shop.\n\n"
        "Чтобы оформить заказ, нажмите «Оформить заказ».\n"
        "После этого мы уточним данные товара и проверим наличие.\n\n"
        "Условия заказа\n"
        "• 50% — предоплата при оформлении\n"
        "• 5–10 дней — ориентировочный срок доставки\n"
        "• 50% — оплата после получения товара\n\n"
        "По любым вопросам — напишите нам.\n\n"
        "Ruby Shop\n"
        "Онлайн-магазин • Донецк"
    )

    await message.answer(
        text,
        reply_markup=main_keyboard
    )


# =========================
# УСЛОВИЯ
# =========================

@dp.message(F.text == "Условия заказа")
async def conditions(message: Message):

    text = (
        "🛍️ Выбор товара\n"
        "Выбираете понравившийся товар и оформляете заказ прямо в боте Ruby Shop. "
        "Бот последовательно запросит необходимые данные и сформирует ваш заказ.\n\n"

        "🔗 Ссылка на товар\n"
        "При оформлении заказа отправьте ссылку на конкретный товар "
        "из Telegram-канала Ruby Shop. Это поможет нам быстро найти нужную модель "
        "и избежать ошибок при оформлении заказа.\n\n"

        "💳 Предоплата\n"
        "Для подтверждения заказа вносится предоплата — 50% от стоимости товара. "
        "После подтверждения мы запускаем заказ в работу.\n\n"

        "📦 Доставка\n"
        "Товар поступает к нам в Донецк в течение 5–10 дней.\n"
        "Срок является ориентировочным и может немного изменяться.\n\n"

        "🤍 Получение товара\n"
        "После поступления товара в Донецк вы получаете заказ и оплачиваете "
        "оставшиеся 50% стоимости.\n\n"

        "Весь процесс — от выбора товара до получения заказа — проходит через Ruby Shop.\n\n"

        "С любовью, Ruby Shop 💋\n"
        "Онлайн-магазин • Донецк"
    )

    await message.answer(text)


# =========================
# НАЧАЛО ЗАКАЗА
# =========================

@dp.message(F.text == "Оформить заказ")
async def start_order(message: Message, state: FSMContext):

    await state.clear()
    await state.set_state(Order.product)

    await message.answer(
        "🛍️ Отправьте товар, который хотите заказать.\n\n"
        "Можно переслать сообщение с товаром из нашего Telegram-канала "
        "или отправить ссылку на товар.",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================
# ТОВАР
# =========================

@dp.message(Order.product)
async def get_product(message: Message, state: FSMContext):

    product_photo = None
    product_text = None
    product_link = None

    # ---------------------------------
    # Если клиент переслал пост
    # Фото + текст под фотографией
    # ---------------------------------

    if message.photo:

        product_photo = message.photo[-1].file_id

        if message.caption:
            product_text = message.caption.strip()

        # Если это пересланный пост из канала,
        # пытаемся автоматически восстановить ссылку
        if message.forward_origin:

            origin = message.forward_origin

            if hasattr(origin, "chat") and hasattr(origin, "message_id"):

                chat = origin.chat

                if getattr(chat, "username", None):
                    product_link = (
                        f"https://t.me/{chat.username}/{origin.message_id}"
                    )

    # ---------------------------------
    # Если клиент просто отправил ссылку
    # ---------------------------------

    elif message.text:

        product_text = message.text.strip()

        if "https://" in product_text or "http://" in product_text:
            product_link = product_text

    # ---------------------------------
    # Ничего подходящего
    # ---------------------------------

    else:

        await message.answer(
            "Пожалуйста, пересылайте пост с товаром "
            "из нашего Telegram-канала или отправьте ссылку на товар."
        )

        return

    await state.update_data(
        product_photo=product_photo,
        product_text=product_text,
        product_link=product_link,
    )

    await state.set_state(Order.color)

    await message.answer(
        "🎨 Укажите цвет товара."
    )


# =========================
# ЦВЕТ
# =========================

@dp.message(Order.color)
async def get_color(message: Message, state: FSMContext):

    await state.update_data(
        color=message.text
    )

    await state.set_state(Order.size)

    await message.answer(
        "📏 Укажите размер."
    )


# =========================
# РАЗМЕР
# =========================

@dp.message(Order.size)
async def get_size(message: Message, state: FSMContext):

    await state.update_data(
        size=message.text
    )

    await state.set_state(Order.quantity)

    await message.answer(
        "🔢 Укажите количество."
    )


# =========================
# КОЛИЧЕСТВО
# =========================

@dp.message(Order.quantity)
async def get_quantity(message: Message, state: FSMContext):

    await state.update_data(
        quantity=message.text
    )

    user = message.from_user

    if user.username:
        username = f"@{user.username}"
    else:
        username = "username не установлен"

    await state.update_data(
        full_name=user.full_name,
        telegram_username=username,
        telegram_id=user.id,
    )

    await state.set_state(Order.phone)

    await message.answer(
        "📱 Номер телефона\n\n"
        "Вы можете передать номер телефона для связи по заказу "
        "или продолжить без него.",
        reply_markup=phone_keyboard
    )


# =========================
# ТЕЛЕФОН — ОТПРАВИТЬ
# =========================

@dp.message(Order.phone, F.contact)
async def get_phone(message: Message, state: FSMContext):

    await state.update_data(
        phone=message.contact.phone_number
    )

    await show_summary(message, state)


# =========================
# ТЕЛЕФОН — НЕ ОТПРАВЛЯТЬ
# =========================

@dp.message(Order.phone, F.text == "Не отправлять номер телефона")
async def skip_phone(message: Message, state: FSMContext):

    await state.update_data(
        phone="Не предоставлен"
    )

    await show_summary(message, state)


# =========================
# СВОДКА
# =========================

async def show_summary(message: Message, state: FSMContext):

    data = await state.get_data()

    product_text = data.get("product_text") or "Описание отсутствует"
    color = data.get("color")
    size = data.get("size")
    quantity = data.get("quantity")
    phone = data.get("phone")
    username = data.get("telegram_username")

    summary = (
        "🛍️ Проверьте данные заказа\n\n"

        f"Товар:\n{product_text}\n\n"
        f"Цвет: {color}\n"
        f"Размер: {size}\n"
        f"Количество: {quantity}\n\n"

        f"Telegram: {username}\n"
        f"Телефон: {phone}\n\n"

        "💳 Условия оплаты:\n"
        "50% — предоплата при оформлении\n"
        "50% — после получения товара\n\n"

        "Всё верно?"
    )

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Да, оформить заказ",
        callback_data="confirm_order"
    )

    builder.button(
        text="Нет, начать заново",
        callback_data="cancel_order"
    )

    builder.adjust(1)

    await state.set_state(Order.confirm)

    await message.answer(
        summary,
        reply_markup=builder.as_markup()
    )


# =========================
# ПОДТВЕРЖДЕНИЕ
# =========================

@dp.callback_query(Order.confirm, F.data == "confirm_order")
async def confirm_order(callback, state: FSMContext):

    data = await state.get_data()

    product_photo = data.get("product_photo")
    product_text = data.get("product_text") or "Описание отсутствует"
    product_link = data.get("product_link")
    color = data.get("color")
    size = data.get("size")
    quantity = data.get("quantity")
    phone = data.get("phone")
    username = data.get("telegram_username")
    telegram_id = data.get("telegram_id")
    full_name = data.get("full_name")

    admin_text = (
        "🔴 НОВЫЙ ЗАКАЗ — RUBY SHOP\n\n"

        "👤 КЛИЕНТ\n"
        f"Имя: {full_name}\n"
        f"Telegram: {username}\n"
        f"Telegram ID: {telegram_id}\n"
        f"Телефон: {phone}\n\n"

        "🛍️ ТОВАР\n"
        f"{product_text}\n\n"

        f"🎨 Цвет: {color}\n"
        f"📏 Размер: {size}\n"
        f"🔢 Количество: {quantity}\n\n"

        "💳 ОПЛАТА\n"
        "50% — предоплата\n"
        "50% — после получения\n"
    )

    if product_link:
        admin_text += (
            "\n🔗 Ссылка на товар:\n"
            f"{product_link}\n"
        )

    # Отправляем тебе фото + текст товара
    if product_photo:

        await bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=product_photo,
            caption=admin_text
        )

    else:

        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text
        )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "✅ Заказ оформлен.\n\n"
        "Мы получили ваш заказ и свяжемся с вами для подтверждения "
        "наличия товара и дальнейшего оформления.\n\n"
        "Ruby Shop",
        reply_markup=main_keyboard
    )

    await state.clear()
    await callback.answer()


# =========================
# НАЧАТЬ ЗАНОВО
# =========================

@dp.callback_query(Order.confirm, F.data == "cancel_order")
async def cancel_order(callback, state: FSMContext):

    await state.clear()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "Хорошо. Давайте оформим заказ заново.\n\n"
        "Нажмите «Оформить заказ».",
        reply_markup=main_keyboard
    )

    await callback.answer()


# =========================
# ВОПРОС
# =========================

@dp.message(F.text == "Задать вопрос")
async def ask_question(message: Message, state: FSMContext):

    await state.set_state(Question.waiting)

    await message.answer(
        "Напишите ваш вопрос одним сообщением.\n\n"
        "Мы передадим его менеджеру Ruby Shop.",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(Question.waiting)
async def receive_question(message: Message, state: FSMContext):

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
        "✅ Вопрос отправлен.\n"
        "Мы свяжемся с вами, как только сможем.",
        reply_markup=main_keyboard
    )

    await state.clear()


# =========================
# ЗАПУСК
# =========================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
