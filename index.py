import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
import aiofiles
import os

from config import BOT_TOKEN, MEMBERS_FILE

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Функция для загрузки участников из JSON файла
async def load_members():
    """Загружает список участников из JSON файла"""
    try:
        async with aiofiles.open(MEMBERS_FILE, 'r', encoding='utf-8') as file:
            content = await file.read()
            data = json.loads(content)
            
            # Проверяем структуру данных
            if isinstance(data, dict):
                return data.get('members', [])
            elif isinstance(data, list):
                return data
            else:
                return []
    except FileNotFoundError:
        logging.error(f"Файл {MEMBERS_FILE} не найден!")
        return []
    except json.JSONDecodeError:
        logging.error(f"Ошибка в формате JSON файла {MEMBERS_FILE}")
        return []

# Функция для сохранения участников в JSON файл
async def save_members(members):
    """Сохраняет список участников в JSON файл"""
    try:
        data = {'members': members}
        async with aiofiles.open(MEMBERS_FILE, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(data, ensure_ascii=False, indent=4))
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла: {e}")
        return False

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для тегания участников.\n\n"
        "Доступные команды:\n"
        "/tag - тегнуть всех участников\n"
        "/list - показать список участников\n"
        "/add @username - добавить участника\n"
        "/remove @username - удалить участника\n"
        "/clear - очистить список\n"
        "/help - показать это сообщение"
    )

# Команда /help
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await cmd_start(message)

# Команда для тегания всех участников
@dp.message_handler(commands=['tag'])
async def cmd_tag(message: types.Message):
    members = await load_members()
    
    if not members:
        await message.answer("❌ Список участников пуст!")
        return
    
    # Проверяем, что бот находится в группе
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("❌ Эта команда работает только в группах!")
        return
    
    # Создаем текст с тегами
    tags = ' '.join(members)
    
    # Проверяем длину сообщения
    if len(tags) > 4000:
        chunk_size = 50
        for i in range(0, len(members), chunk_size):
            chunk = members[i:i + chunk_size]
            await message.answer(' '.join(chunk))
            await asyncio.sleep(0.5)
    else:
        await message.answer(f"👥 Тегаю всех:\n{tags}")

# Команда для показа списка участников
@dp.message_handler(commands=['list'])
async def cmd_list(message: types.Message):
    members = await load_members()
    
    if not members:
        await message.answer("📋 Список участников пуст!")
        return
    
    members_list = '\n'.join([f"{i+1}. {member}" for i, member in enumerate(members)])
    await message.answer(f"📋 Список участников ({len(members)}):\n\n{members_list}")

# Команда для добавления участника
@dp.message_handler(commands=['add'])
async def cmd_add(message: types.Message):
    args = message.get_args().strip()
    
    if not args:
        await message.answer("❌ Укажите username для добавления!\nПример: /add @username")
        return
    
    if not args.startswith('@'):
        args = '@' + args
    
    members = await load_members()
    
    if args in members:
        await message.answer(f"❌ Участник {args} уже есть в списке!")
        return
    
    members.append(args)
    
    if await save_members(members):
        await message.answer(f"✅ Участник {args} успешно добавлен!")
    else:
        await message.answer("❌ Ошибка при сохранении списка!")

# Команда для удаления участника
@dp.message_handler(commands=['remove'])
async def cmd_remove(message: types.Message):
    args = message.get_args().strip()
    
    if not args:
        await message.answer("❌ Укажите username для удаления!\nПример: /remove @username")
        return
    
    if not args.startswith('@'):
        args = '@' + args
    
    members = await load_members()
    
    if args not in members:
        await message.answer(f"❌ Участник {args} не найден в списке!")
        return
    
    members.remove(args)
    
    if await save_members(members):
        await message.answer(f"✅ Участник {args} успешно удален!")
    else:
        await message.answer("❌ Ошибка при сохранении списка!")

# Команда для очистки списка
@dp.message_handler(commands=['clear'])
async def cmd_clear(message: types.Message):
    if await save_members([]):
        await message.answer("✅ Список участников очищен!")
    else:
        await message.answer("❌ Ошибка при очистке списка!")

# ⚠️ ВАЖНО: Обрабатываем ТОЛЬКО неизвестные команды (начинающиеся с /)
@dp.message_handler(lambda message: message.text and message.text.startswith('/'))
async def unknown_command(message: types.Message):
    await message.answer("❌ Неизвестная команда. Используйте /help для списка команд.")

# Запуск бота
if __name__ == '__main__':
    # Создаем или проверяем файл members.json
    if not os.path.exists(MEMBERS_FILE):
        with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'members': []}, f, ensure_ascii=False, indent=4)
        print(f"✅ Создан файл {MEMBERS_FILE}")
    else:
        # Проверяем структуру существующего файла
        try:
            with open(MEMBERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({'members': data}, f, ensure_ascii=False, indent=4)
                print(f"✅ Файл {MEMBERS_FILE} преобразован в правильный формат")
        except:
            pass
    
    print("🚀 Бот запущен!")
    print("📝 Бот отвечает ТОЛЬКО на команды, начинающиеся с /")
    print("💬 Обычные сообщения в чате игнорируются")
    executor.start_polling(dp, skip_updates=True)
