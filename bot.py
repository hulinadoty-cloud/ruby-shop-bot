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
        "После этого мы уточним данные по товару и проверим наличие.\n\n"
        "· · ·\n\n"
        "Условия заказа\n"
        "• 50% — предоплата при оформлении\n"
        "• 5–10 дней — ориентировочный срок доставки\n"
        "• 50% — оплата после получения товара\n\n"
        "· · ·\n\n"
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
        "• 50% — оплата после получения товара\n\n"
        "Перед оформлением мы обязательно проверяем наличие товара."
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
        await state.update_data(product="Фото товара прикреплено")
    elif message.text:
        await state.update_data(product=message.text)
    else:
        await message.answer("Отправьте фото товара или ссылку на пост.")
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

    data = await state.get_data()

    summary = (
        "Проверьте данные заказа:\n\n"
        f"Товар: {data['product']}\n"
        f"Цвет: {data['color']}\n"
        f"Размер: {data['size']}\n"
        f"Количество: {data['quantity']}\n\n"
        "Если всё верно, напишите «Да».\n"
        "Если нужно изменить данные — напишите «Нет»."
    )

    await state.set_state(Order.confirm)
    await message.answer(summary)


@dp.message(Order.confirm)
async def confirm_order(message: Message, state: FSMContext):
    answer = message.text.lower().strip()

    if answer == "нет":
        await state.clear()
        await message.answer(
            "Хорошо. Нажмите «Оформить заказ», чтобы заполнить заказ заново.",
            reply_markup=menu
        )
        return

    if answer != "да":
        await message.answer("Напишите «Да», если всё верно, или «Нет», чтобы начать заново.")
        return

    data = await state.get_data()

    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"

    admin_message = (
        "НОВЫЙ ЗАКАЗ — RUBY SHOP\n\n"
        f"Клиент: {username}\n"
        f"Telegram ID: {message.from_user.id}\n\n"
        f"Товар: {data['product']}\n"
        f"Цвет: {data['color']}\n"
        f"Размер: {data['size']}\n"
        f"Количество: {data['quantity']}"
    )

    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_message
    )

    await state.clear()

    await message.answer(
        "Заказ принят.\n\n"
        "Мы проверим наличие товара и свяжемся с вами для оформления "
        "предоплаты 50%.\n\n"
        "Спасибо, что выбираете Ruby Shop.",
        reply_markup=menu
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
