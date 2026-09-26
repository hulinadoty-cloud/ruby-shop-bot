import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestUsers,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
class Order(StatesGroup):
    product = State()
    color = State()
    size = State()
    quantity = State()
    username = State()
    confirm = State()
class Question(StatesGroup):
    waiting = State()
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Оформить заказ")],
        [KeyboardButton(text="Условия заказа")],
        [KeyboardButton(text="Задать вопрос")]
    ],
    resize_keyboard=True
)
# Кнопка для автоматической передачи Telegram-аккаунта
username_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="Отправить мой Telegram",
                request_users=KeyboardButtonRequestUsers(
                    request_id=1,
                    user_is_bot=False,
                    max_quantity=1,
                    request_username=True,
                    request_name=True
                )
            )
        ],
        [KeyboardButton(text="Указать username вручную")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
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
        "Онлайн-магазин одежды · Донецк",
        reply_markup=menu
    )
@dp.message(F.text == "Условия заказа")
async def conditions(message: Message):
    await message.answer(
        "Условия заказа\n\n"
        "• 50% — предоплата при оформлении\n"
        "• 5–10 дней — ориентировочный срок доставки\n"
        "• 50% — оплата после получения товара"
    )
# =========================
# ВОПРОСЫ
# =========================
@dp.message(F.text == "Задать вопрос")
async def question_start(message: Message, state: FSMContext):
    await state.set_state(Question.waiting)
    await message.answer(
        "Напишите ваш вопрос следующим сообщением.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
    )
@dp.message(Question.waiting)
async def receive_question(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "отмена":
        await state.clear()
        await message.answer(
            "Хорошо.",
            reply_markup=menu
        )
        return
    user = message.from_user
    username = (
        f"@{user.username}"
        if user.username
        else "username не установлен"
    )
    admin_message = (
        "❓ НОВЫЙ ВОПРОС — RUBY SHOP\n\n"
        "КЛИЕНТ\n"
        f"Имя: {user.full_name}\n"
        f"Username: {username}\n"
        f"Telegram ID: {user.id}\n\n"
        "ВОПРОС\n"
    )
    if message.text:
        admin_message += message.text
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message
        )
    elif message.photo:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message + "Клиент отправил фотографию."
        )
        await bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=message.photo[-1].file_id
        )
    elif message.video:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message + "Клиент отправил видео."
        )
        await bot.send_video(
            chat_id=ADMIN_CHAT_ID,
            video=message.video.file_id
        )
    else:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message + "Клиент отправил сообщение."
        )
    await state.clear()
    await message.answer(
        "Ваш вопрос отправлен.\n"
        "Мы свяжемся с вами, как только сможем.",
        reply_markup=menu
    )
# =========================
# ЗАКАЗ
# =========================
@dp.message(F.text == "Оформить заказ")
async def start_order(message: Message, state: FSMContext):
    await state.set_state(Order.product)
    await message.answer(
        "Оформление заказа\n\n"
        "Отправьте фото товара или ссылку на пост с товаром."
    )
@dp.message(Order.product)
async def get_product(message: Message, state: FSMContext):
    if message.photo:
        photo_id = message.photo[-1].file_id
        await state.update_data(
            product_type="photo",
            product_photo_id=photo_id,
            product="Фото товара"
        )
    elif message.text:
        await state.update_data(
            product_type="text",
            product=message.text
        )
    else:
        await message.answer(
            "Отправьте фото товара или ссылку на пост."
        )
        return
    await state.set_state(Order.color)
    await message.answer("Укажите желаемый цвет.")
@dp.message(Order.color)
async def get_color(message: Message, state: FSMContext):
    await state.update_data(color=message.text)
    await state.set_state(Order.size)
    await message.answer("Укажите размер.")
@dp.message(Order.size)
async def get_size(message: Message, state: FSMContext):
    await state.update_data(size=message.text)
    await state.set_state(Order.quantity)
    await message.answer("Укажите количество.")
@dp.message(Order.quantity)
async def get_quantity(message: Message, state: FSMContext):
    await state.update_data(quantity=message.text)
    await state.set_state(Order.username)
    await message.answer(
        "Укажите ваш Telegram username.",
        reply_markup=username_keyboard
    )
# =========================
# АВТОМАТИЧЕСКИЙ USERNAME
# =========================
@dp.message(
    Order.username,
    F.users_shared
)
async def get_username_automatically(
    message: Message,
    state: FSMContext
):
    shared_user = message.users_shared.users[0]
    username = shared_user.username
    if username:
        username = f"@{username}"
    else:
        username = "username не установлен"
    await state.update_data(
        customer_username=username
    )
    await show_order_summary(message, state)
# =========================
# USERNAME ВРУЧНУЮ
# =========================
@dp.message(
    Order.username,
    F.text == "Указать username вручную"
)
async def manual_username_start(
    message: Message,
    state: FSMContext
):
    await message.answer(
        "Введите ваш Telegram username.\n\n"
        "Например: @username"
    )
@dp.message(Order.username)
async def get_username_manually(
    message: Message,
    state: FSMContext
):
    username = message.text.strip()
    if not username:
        await message.answer(
            "Введите username или нажмите кнопку «Отправить мой Telegram»."
        )
        return
    if not username.startswith("@"):
        username = "@" + username
    await state.update_data(
        customer_username=username
    )
    await show_order_summary(message, state)
async def show_order_summary(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()
    summary = (
        "Проверьте данные заказа:\n\n"
        f"Товар: {data['product']}\n"
        f"Цвет: {data['color']}\n"
        f"Размер: {data['size']}\n"
        f"Количество: {data['quantity']}\n"
        f"Telegram username: {data['customer_username']}\n\n"
        "Если всё верно — напишите «Да».\n"
        "Если нужно начать заново — напишите «Нет»."
    )
    await state.set_state(Order.confirm)
    await message.answer(
        summary,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Да")],
                [KeyboardButton(text="Нет")]
            ],
            resize_keyboard=True
        )
    )
# =========================
# ПОДТВЕРЖДЕНИЕ ЗАКАЗА
# =========================
@dp.message(Order.confirm)
async def confirm_order(
    message: Message,
    state: FSMContext
):
    answer = message.text.lower().strip()
    if answer == "нет":
        await state.clear()
        await message.answer(
            "Хорошо. Нажмите «Оформить заказ», чтобы начать заново.",
            reply_markup=menu
        )
        return
    if answer != "да":
        await message.answer(
            "Напишите «Да», если всё верно, или «Нет», чтобы начать заново."
        )
        return
    data = await state.get_data()
    user = message.from_user
    telegram_username = (
        f"@{user.username}"
        if user.username
        else "username не установлен"
    )
    customer_username = data.get(
        "customer_username",
        "не указан"
    )
    admin_message = (
        "🛍 НОВЫЙ ЗАКАЗ — RUBY SHOP\n\n"
        "👤 КЛИЕНТ\n"
        f"Имя: {user.full_name}\n"
        f"Username клиента: {customer_username}\n"
        f"Username Telegram: {telegram_username}\n"
        f"Telegram ID: {user.id}\n\n"
        "📦 ЗАКАЗ\n"
        f"Товар: {data['product']}\n"
        f"Цвет: {data['color']}\n"
        f"Размер: {data['size']}\n"
        f"Количество: {data['quantity']}\n\n"
        "💳 УСЛОВИЯ\n"
        "50% — предоплата\n"
        "50% — после получения"
    )
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_message
    )
    if data.get("product_type") == "photo":
        await bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=data["product_photo_id"],
            caption="📸 Фото товара из заказа."
        )
    elif data.get("product_type") == "text":
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔗 Товар / ссылка:\n{data['product']}"
        )
    await state.clear()
    await message.answer(
        "Заказ принят.\n\n"
        "Мы проверим наличие товара и свяжемся с вами "
        "для оформления предоплаты 50%.\n\n"
        "Спасибо, что выбираете Ruby Shop.",
        reply_markup=menu
    )
async def main():
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
