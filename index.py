import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.markdown import text
import aiofiles

from config import BOT_TOKEN, MEMBERS_FILE

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция для загрузки участников
async def load_members():
    """Загружает список участников из JSON файла"""
    try:
        async with aiofiles.open(MEMBERS_FILE, 'r', encoding='utf-8') as file:
            content = await file.read()
            data = json.loads(content)
            
            if isinstance(data, dict):
                return data.get('members', [])
            elif isinstance(data, list):
                return data
            else:
                return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

# Функция для сохранения участников
async def save_members(members):
    """Сохраняет список участников в JSON файл"""
    try:
        data = {'members': members}
        async with aiofiles.open(MEMBERS_FILE, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(data, ensure_ascii=False, indent=4))
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении: {e}")
        return False

# Команда /start
@dp.message(Command('start'))
async def cmd_start(message: Message):
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
@dp.message(Command('help'))
async def cmd_help(message: Message):
    await cmd_start(message)

# Команда для тегания всех участников
@dp.message(Command('tag'))
async def cmd_tag(message: Message):
    members = await load_members()
    
    if not members:
        await message.answer("❌ Список участников пуст!")
        return
    
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("❌ Эта команда работает только в группах!")
        return
    
    tags = ' '.join(members)
    
    if len(tags) > 4000:
        chunk_size = 50
        for i in range(0, len(members), chunk_size):
            chunk = members[i:i + chunk_size]
            await message.answer(' '.join(chunk))
            await asyncio.sleep(0.5)
    else:
        await message.answer(f"👥 Тегаю всех:\n{tags}")

# Команда для показа списка
@dp.message(Command('list'))
async def cmd_list(message: Message):
    members = await load_members()
    
    if not members:
        await message.answer("📋 Список участников пуст!")
        return
    
    members_list = '\n'.join([f"{i+1}. {member}" for i, member in enumerate(members)])
    await message.answer(f"📋 Список участников ({len(members)}):\n\n{members_list}")

# Команда для добавления
@dp.message(Command('add'))
async def cmd_add(message: Message):
    args = message.text.replace('/add', '').strip()
    
    if not args:
        await message.answer("❌ Укажите username!\nПример: /add @username")
        return
    
    if not args.startswith('@'):
        args = '@' + args
    
    members = await load_members()
    
    if args in members:
        await message.answer(f"❌ Участник {args} уже есть!")
        return
    
    members.append(args)
    
    if await save_members(members):
        await message.answer(f"✅ Участник {args} добавлен!")
    else:
        await message.answer("❌ Ошибка сохранения!")

# Команда для удаления
@dp.message(Command('remove'))
async def cmd_remove(message: Message):
    args = message.text.replace('/remove', '').strip()
    
    if not args:
        await message.answer("❌ Укажите username!\nПример: /remove @username")
        return
    
    if not args.startswith('@'):
        args = '@' + args
    
    members = await load_members()
    
    if args not in members:
        await message.answer(f"❌ Участник {args} не найден!")
        return
    
    members.remove(args)
    
    if await save_members(members):
        await message.answer(f"✅ Участник {args} удален!")
    else:
        await message.answer("❌ Ошибка сохранения!")

# Команда для очистки
@dp.message(Command('clear'))
async def cmd_clear(message: Message):
    if await save_members([]):
        await message.answer("✅ Список очищен!")
    else:
        await message.answer("❌ Ошибка!")

# Обработчик неизвестных команд
@dp.message(lambda message: message.text and message.text.startswith('/'))
async def unknown_command(message: Message):
    await message.answer("❌ Неизвестная команда. Используйте /help")

# Запуск бота
async def main():
    # Проверяем и создаем файл если нужно
    if os.path.exists(MEMBERS_FILE):
        try:
            with open(MEMBERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({'members': data}, f, ensure_ascii=False, indent=4)
                print("✅ Существующие данные сконвертированы")
        except:
            pass
    else:
        with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'members': []}, f, ensure_ascii=False, indent=4)
        print(f"✅ Создан файл {MEMBERS_FILE}")
    
    print("🚀 Бот запущен!")
    print("📝 Бот отвечает ТОЛЬКО на команды")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
