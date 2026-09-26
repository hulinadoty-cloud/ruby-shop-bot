import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
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
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Оформить заказ")],
        [KeyboardButton(text="Условия заказа")],
        [KeyboardButton(text="Задать вопрос")]
    ],
    resize_keyboard=True
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
@dp.message(F.text == "Задать вопрос")
async def question(message: Message):
    await message.answer(
        "Напишите ваш вопрос следующим сообщением.\n"
        "Мы обязательно ответим."
    )
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
        "Укажите ваш Telegram username.\n\n"
        "Например: @username\n"
        "Если у вас нет username, напишите «нет»."
    )
@dp.message(Order.username)
async def get_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if not username:
        await message.answer(
            "Пожалуйста, укажите ваш Telegram username "
            "или напишите «нет»."
        )
        return
    if username.lower() == "нет":
        username = "username не указан"
    elif not username.startswith("@"):
        username = "@" + username
    await state.update_data(customer_username=username)
    data = await state.get_data()
    summary = (
        "Проверьте данные заказа:\n\n"
        f"Товар: {data['product']}\n"
        f"Цвет: {data['color']}\n"
        f"Размер: {data['size']}\n"
        f"Количество: {data['quantity']}\n"
        f"Telegram username: {username}\n\n"
        "Если всё верно — напишите «Да».\n"
        "Если нужно начать заново — напишите «Нет»."
    )
    await state.set_state(Order.confirm)
    await message.answer(summary)
@dp.message(Order.confirm)
async def confirm_order(message: Message, state: FSMContext):
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
    # Username, который человек указал сам
    customer_username = data.get(
        "customer_username",
        "username не указан"
    )
    # Автоматический username Telegram, если он есть
    telegram_username = (
        f"@{user.username}"
        if user.username
        else "не установлен"
    )
    full_name = user.full_name
    admin_message = (
        "НОВЫЙ ЗАКАЗ — RUBY SHOP\n\n"
        "КЛИЕНТ\n"
        f"Имя: {full_name}\n"
        f"Username клиента: {customer_username}\n"
        f"Username Telegram: {telegram_username}\n"
        f"Telegram ID: {user.id}\n\n"
        "ЗАКАЗ\n"
        f"Товар: {data['product']}\n"
        f"Цвет: {data['color']}\n"
        f"Размер: {data['size']}\n"
        f"Количество: {data['quantity']}\n\n"
        "УСЛОВИЯ\n"
        "50% — предоплата\n"
        "50% — после получения"
    )
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_message
    )
    # Если клиент отправил фото товара
    if data.get("product_type") == "photo":
        await bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=data["product_photo_id"],
            caption="Фото товара из заказа."
        )
    # Если клиент отправил ссылку
    elif data.get("product_type") == "text":
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Ссылка / товар:\n{data['product']}"
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
