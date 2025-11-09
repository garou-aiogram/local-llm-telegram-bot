import asyncio
import base64
import logging
import os
from datetime import datetime
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GemmaImageBot:
    def __init__(self, bot_token: str):
        self.client = AsyncOpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio"
        )
        self.bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()

        # Создаем папку для сохранения фото
        self.photos_folder = "user_photos"
        os.makedirs(self.photos_folder, exist_ok=True)

        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков сообщений"""
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_help, Command("help"))
        self.dp.message.register(self.handle_image, F.photo)
        self.dp.message.register(self.handle_text, F.text)
        self.dp.message.register(self.handle_other_messages)

    def save_image(self, image_data: bytes, user_id: int) -> str:
        """Сохраняет изображение в папку и возвращает путь"""
        try:
            # Создаем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_{user_id}_{timestamp}.jpg"
            filepath = os.path.join(self.photos_folder, filename)

            # Сохраняем изображение
            with open(filepath, "wb") as f:
                f.write(image_data)

            logger.info(f"Изображение сохранено: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Ошибка сохранения изображения: {e}")
            return None

    async def image_to_base64(self, image_data: bytes) -> str:
        """Конвертирует изображение в base64 строку"""
        try:
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка конвертации изображения: {e}")
            raise

    async def describe_image(self, image_data: bytes, max_tokens: int = 500) -> str:
        """Асинхронно получает описание изображения от модели"""
        try:
            # Конвертируем изображение в base64
            base64_image = await self.image_to_base64(image_data)

            logger.info("Отправляем изображение в нейросеть...")

            # Отправляем запрос к модели
            response = await self.client.chat.completions.create(
                model="google_gemma-3-12b-it",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Ты - AI помощник для описания изображений. 
                                Подробно опиши что изображено на картинке. 
                                Опиши сцену, объекты, цвета, композицию, настроение и любые важные детали. 
                                Будь максимально информативным и используй русский язык."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                stream=False
            )

            description = response.choices[0].message.content
            logger.info("Описание изображения получено успешно")
            return description

        except Exception as e:
            logger.error(f"Ошибка при анализе изображения: {e}")
            return f"❌ Произошла ошибка при анализе изображения: {str(e)}"

    async def generate_text_response(self, text: str) -> str:
        #"""Генерация ответа на текстовое сообщение"""
        try:
            response = await self.client.chat.completions.create(
                model='google_gemma-3-12b-it',
                messages=[
                    {
                        'role': "system",
                        "content": """Ты дружелюбный AI-помощник. Отвечай на русском языке. 
                        Ты также умеешь анализировать изображения - пользователи могут отправлять тебе картинки."""
                    },
                    {'role': "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Ошибка нейросети: {e}")
            return "❌ Произошла ошибка при обращении к нейросети."

    async def cmd_start(self, message: Message):
        #"""Обработчик команды /start"""
        await message.answer(
            "🖼️ <b>Добро пожаловать в бот с анализом изображений!</b>\n\n"
            "Я умею:\n"
            "• 📖 Отвечать на текстовые сообщения\n"
            "• 🖼️ Анализировать и описывать изображения\n"
            "• 💾 Автоматически сохранять все отправленные фото\n\n"
            "Просто отправьте мне картинку или текст!"
        )

    async def cmd_help(self, message: Message):
        #"""Обработчик команды /help"""
        await message.answer(
            "📚 <b>Справка</b>\n\n"
            "<b>Команды:</b>\n"
            "/start - начать работу\n"
            "/help - показать справку\n\n"
            "<b>Что я умею:</b>\n"
            "• Отвечать на текстовые сообщения\n"
            "• Анализировать и описывать изображения\n"
            "• Сохранять все отправленные фото в папку\n\n"
            "Просто отправьте мне:\n"
            "📝 Текст - для общения\n"
            "🖼️ Изображение - для анализа"
        )

    async def handle_image(self, message: Message):
        """Обработчик изображений"""
        processing_msg = None
        try:
            # Отправляем сообщение о начале обработки
            processing_msg = await message.answer("🔄 <b>Обрабатываю изображение...</b>")

            # Показываем статус "печатает"
            await message.bot.send_chat_action(
                chat_id=message.chat.id,
                action="typing"
            )

            # Получаем файл изображения
            file_id = message.photo[-1].file_id
            file = await message.bot.get_file(file_id)
            file_data = await message.bot.download_file(file.file_path)
            image_bytes = file_data.read()

            # Сохраняем изображение
            saved_path = self.save_image(image_bytes, message.from_user.id)
            save_status = "✅ Фото сохранено" if saved_path else "❌ Не удалось сохранить фото"

            # Анализируем изображение
            description = await self.describe_image(image_bytes)

            # Удаляем сообщение "Обрабатываю изображение"
            if processing_msg:
                await processing_msg.delete()

            # Отправляем описание
            await message.answer(
                f"🖼️ <b>Описание изображения:</b>\n\n"
                f"{description}\n\n"
                f"<i>{save_status}</i>"
            )

        except Exception as e:
            logger.error(f"Ошибка обработки изображения: {e}")

            # Удаляем сообщение "Обрабатываю изображение" если была ошибка
            if processing_msg:
                await processing_msg.delete()

            await message.answer("❌ Произошла ошибка при обработке изображения.")

    async def handle_text(self, message: Message):
        """Обработчик текстовых сообщений"""
        # Показываем статус "печатает"
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )

        # Получаем ответ от нейросети
        response = await self.generate_text_response(message.text)

        # Отправляем ответ
        await message.answer(response)

    async def handle_other_messages(self, message: Message):
        """Обработчик других типов сообщений"""
        await message.answer("📝 Отправьте мне текстовое сообщение или изображение для анализа.")

    async def get_photos_stats(self) -> dict:
        """Получает статистику по сохраненным фото"""
        try:
            photos = [f for f in os.listdir(self.photos_folder) if f.endswith(('.jpg', '.jpeg', '.png'))]
            return {
                'total_photos': len(photos),
                'folder_size': sum(os.path.getsize(os.path.join(self.photos_folder, f)) for f in photos)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {'total_photos': 0, 'folder_size': 0}

    async def run(self):
        """Запуск бота"""
        logger.info("Запуск бота с анализом изображений...")

        # Проверяем и выводим статистику папки
        stats = await self.get_photos_stats()
        logger.info(f"Папка для фото: {self.photos_folder}")
        logger.info(f"Сохранено фото: {stats['total_photos']}")
        logger.info(f"Размер папки: {stats['folder_size'] / 1024 / 1024:.2f} MB")

        try:
            # Запускаем бота
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
        finally:
            await self.bot.session.close()


# Запуск бота
async def main():
    bot_token = "YOUR_BOT_TOKEN"
    bot = GemmaImageBot(bot_token)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())