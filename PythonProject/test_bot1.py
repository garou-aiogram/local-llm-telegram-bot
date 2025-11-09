import asyncio
import logging
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI для LM Studio
client = AsyncOpenAI(
    base_url='http://127.0.0.1:1234/v1',
    api_key='lm-studio'  # Обычно для LM Studio можно использовать любую строку
)

# Создаем бота и диспетчер
bot = Bot(token="7909527139:AAHyfy21fMAY-qtYNiZ7E6FatXA4TXTELis")  # Замени на свой токен
dp = Dispatcher()


async def generate_response(text: str) -> str:
    """
    Функция для генерации ответа от нейросети
    """
    try:
        response = await client.chat.completions.create(
            model='google_gemma-3-12b-it',
            messages=[
                {'role': "system", "content": "Ты дружелюбный помощник. Отвечай на русском языке."},
                {'role': "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        logger.info(f"Запрос: {text}")
        logger.info(f"Ответ нейросети: {response.choices[0].message.content}")

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Ошибка при обращении к нейросети: {e}")
        return "Извините, произошла ошибка при обращении к нейросети. Попробуйте позже."


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! 👋 Я бот с интегрированной нейросетью Gemma.\n"
        "Просто напиши мне сообщение, и я постараюсь на него ответить!"
    )


# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - начать работу\n"
        "/help - показать справку\n\n"
        "Просто напиши любой вопрос или сообщение, и я отвечу!"
    )


# Обработчик текстовых сообщений
@dp.message(F.text)
async def handle_text(message: Message):
    # Показываем, что бот печатает
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Получаем ответ от нейросети
    response = await generate_response(message.text)

    # Отправляем ответ пользователю
    await message.answer(response)


# Обработчик не текстовых сообщений
@dp.message()
async def handle_other_messages(message: Message):
    await message.answer("Пожалуйста, отправьте текстовое сообщение.")


async def main():
    logger.info("Бот запускается...")
    try:
        # Проверка подключения к нейросети
        test_response = await generate_response("Привет! Ответь коротко: тест связи.")
        logger.info(f"Тест нейросети: {test_response}")

        # Запуск бота
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())