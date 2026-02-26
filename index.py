import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.utils.markdown import text
import aiofiles

from config import BOT_TOKEN, MEMBERS_FILE

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Функция для загрузки участников
async def load_members():
    """Загружает список участников из JSON файла"""
    try:
        async with aiofiles.open(MEMBERS_FILE, 'r', encoding='utf-8') as file:
            content = await file.read()
            data = json.loads(content)
            
            # Проверяем новую структуру
            if isinstance(data, dict):
                if 'users' in data:
                    return data.get('users', [])
                elif 'members' in data:
                    # Конвертируем старую структуру
                    if isinstance(data['members'], list):
                        new_members = []
                        for item in data['members']:
                            if isinstance(item, str):
                                new_members.append({
                                    'type': 'username',
                                    'value': item
                                })
                            elif isinstance(item, dict):
                                new_members.append(item)
                        return new_members
            elif isinstance(data, list):
                # Конвертируем старый список
                new_members = []
                for item in data:
                    if isinstance(item, str):
                        new_members.append({
                            'type': 'username',
                            'value': item
                        })
                    elif isinstance(item, dict):
                        new_members.append(item)
                return new_members
            return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

# Функция для сохранения участников
async def save_members(members):
    """Сохраняет список участников в JSON файл"""
    try:
        data = {'users': members}
        async with aiofiles.open(MEMBERS_FILE, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(data, ensure_ascii=False, indent=4))
        return True
    except Exception as e:
        logging.error(f"Ошибка при сохранении: {e}")
        return False

# Функция для форматирования списка
def format_members_list(members):
    """Форматирует список участников для отображения"""
    formatted = []
    for i, member in enumerate(members, 1):
        if member['type'] == 'username':
            formatted.append(f"{i}. {member['value']}")
        else:
            formatted.append(f"{i}. {member['name']} (ID: {member['user_id']})")
    return '\n'.join(formatted)

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для тегания участников.\n\n"
        "📝 **Основные команды:**\n"
        "/tag - тегнуть всех участников (только в группе)\n"
        "/list - показать список участников\n\n"
        
        "➕ **Для админов:**\n"
        "/add @username - добавить участника\n"
        "/remove @username - удалить участника\n"
        "/addbyid ID Имя - добавить по ID\n"
        "/clear - очистить список\n\n"
        
        "🔹 **Для участников без username:**\n"
        "/register - зарегистрироваться в боте (в личке)\n"
        "/myname Имя - установить имя (после регистрации)\n"
        "/help - показать это сообщение",
        parse_mode=ParseMode.MARKDOWN
    )

# Команда /help
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await cmd_start(message)

# Команда для регистрации (только в личке)
@dp.message_handler(commands=['register'])
async def cmd_register(message: types.Message):
    # Проверяем, что это личные сообщения
    if message.chat.type != 'private':
        await message.answer("❌ Команда /register работает только в личных сообщениях с ботом!")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Пользователь"
    
    members = await load_members()
    
    # Проверяем, не зарегистрирован ли уже пользователь
    for member in members:
        if member.get('type') == 'id' and member.get('user_id') == user_id:
            await message.answer(f"❌ Вы уже зарегистрированы как {member.get('name')}!")
            return
        if member.get('type') == 'username' and member.get('value') == f"@{username}":
            await message.answer(f"❌ Вы уже зарегистрированы как {member.get('value')}!")
            return
    
    if username:
        # Если есть username
        members.append({
            'type': 'username',
            'value': f"@{username}"
        })
        await save_members(members)
        await message.answer(
            f"✅ Вы успешно зарегистрированы как @{username}!\n\n"
            f"Теперь вас будут тегать в группе."
        )
    else:
        # Если нет username - сохраняем ID
        members.append({
            'type': 'id',
            'user_id': user_id,
            'name': first_name
        })
        await save_members(members)
        await message.answer(
            f"✅ Вы успешно зарегистрированы как {first_name} (ID: {user_id})!\n\n"
            f"Теперь вас будут тегать в группе.\n"
            f"Чтобы изменить имя, используйте /myname НовоеИмя"
        )

# Команда для изменения имени
@dp.message_handler(commands=['myname'])
async def cmd_myname(message: types.Message):
    if message.chat.type != 'private':
        await message.answer("❌ Команда /myname работает только в личных сообщениях!")
        return
    
    args = message.get_args().strip()
    
    if not args:
        await message.answer("❌ Укажите имя!\nПример: /myname Давид")
        return
    
    user_id = message.from_user.id
    members = await load_members()
    
    # Ищем пользователя по ID
    found = False
    for member in members:
        if member.get('type') == 'id' and member.get('user_id') == user_id:
            member['name'] = args
            found = True
            break
    
    if found:
        await save_members(members)
        await message.answer(f"✅ Имя изменено на {args}!")
    else:
        await message.answer("❌ Вы не зарегистрированы! Используйте /register")

# Команда для тегания всех участников
@dp.message_handler(commands=['tag'])
async def cmd_tag(message: types.Message):
    members = await load_members()
    
    if not members:
        await message.answer("❌ Список участников пуст!")
        return
    
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("❌ Эта команда работает только в группах!")
        return
    
    mentions = []
    for member in members:
        if member['type'] == 'username':
            mentions.append(member['value'])
        else:
            # Создаем упоминание через ID
            mention_url = f"tg://user?id={member['user_id']}"
            mention = f"[{member['name']}]({mention_url})"
            mentions.append(mention)
    
    tags = ' '.join(mentions)
    
    if len(tags) > 4000:
        chunk_size = 30
        for i in range(0, len(mentions), chunk_size):
            chunk = mentions[i:i + chunk_size]
            await message.answer(' '.join(chunk), parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.5)
    else:
        await message.answer(f"👥 Тегаю всех:\n{tags}", parse_mode=ParseMode.MARKDOWN)

# Команда для показа списка
@dp.message_handler(commands=['list'])
async def cmd_list(message: types.Message):
    members = await load_members()
    
    if not members:
        await message.answer("📋 Список участников пуст!")
        return
    
    members_list = format_members_list(members)
    await message.answer(f"📋 Список участников ({len(members)}):\n\n{members_list}")

# Команда для добавления по username
@dp.message_handler(commands=['add'])
async def cmd_add(message: types.Message):
    args = message.get_args().strip()
    
    if not args:
        await message.answer("❌ Укажите username!\nПример: /add @username")
        return
    
    if not args.startswith('@'):
        args = '@' + args
    
    members = await load_members()
    
    # Проверяем, есть ли уже такой username
    for member in members:
        if member.get('type') == 'username' and member.get('value') == args:
            await message.answer(f"❌ Участник {args} уже есть!")
            return
    
    members.append({
        'type': 'username',
        'value': args
    })
    
    if await save_members(members):
        await message.answer(f"✅ Участник {args} добавлен!")
    else:
        await message.answer("❌ Ошибка сохранения!")

# Команда для добавления по ID
@dp.message_handler(commands=['addbyid'])
async def cmd_add_by_id(message: types.Message):
    args = message.get_args().strip().split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer("❌ Укажите ID и имя!\nПример: /addbyid 123456789 Давид")
        return
    
    try:
        user_id = int(args[0])
        name = args[1]
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    members = await load_members()
    
    # Проверяем, нет ли уже такого ID
    for member in members:
        if member.get('type') == 'id' and member.get('user_id') == user_id:
            await message.answer(f"❌ Пользователь с ID {user_id} уже есть!")
            return
    
    members.append({
        'type': 'id',
        'user_id': user_id,
        'name': name
    })
    
    if await save_members(members):
        await message.answer(f"✅ Пользователь {name} (ID: {user_id}) добавлен!")
    else:
        await message.answer("❌ Ошибка сохранения!")

# Команда для удаления
@dp.message_handler(commands=['remove'])
async def cmd_remove(message: types.Message):
    args = message.get_args().strip()
    
    if not args:
        await message.answer("❌ Укажите username или ID!\nПример: /remove @username\nИли: /remove 123456789")
        return
    
    members = await load_members()
    
    # Пробуем удалить по username
    if args.startswith('@'):
        for i, member in enumerate(members):
            if member.get('type') == 'username' and member.get('value') == args:
                removed = members.pop(i)
                if await save_members(members):
                    await message.answer(f"✅ Участник {args} удален!")
                else:
                    await message.answer("❌ Ошибка сохранения!")
                return
        await message.answer(f"❌ Участник {args} не найден!")
    
    # Пробуем удалить по ID
    else:
        try:
            user_id = int(args)
            for i, member in enumerate(members):
                if member.get('type') == 'id' and member.get('user_id') == user_id:
                    removed = members.pop(i)
                    if await save_members(members):
                        await message.answer(f"✅ Пользователь {removed.get('name')} удален!")
                    else:
                        await message.answer("❌ Ошибка сохранения!")
                    return
            await message.answer(f"❌ Пользователь с ID {user_id} не найден!")
        except ValueError:
            await message.answer("❌ Неверный формат! Используйте @username или ID")

# Команда для очистки
@dp.message_handler(commands=['clear'])
async def cmd_clear(message: types.Message):
    if await save_members([]):
        await message.answer("✅ Список очищен!")
    else:
        await message.answer("❌ Ошибка!")

# Обработчик неизвестных команд
@dp.message_handler(lambda message: message.text and message.text.startswith('/'))
async def unknown_command(message: types.Message):
    await message.answer("❌ Неизвестная команда. Используйте /help")

# Запуск бота
if __name__ == '__main__':
    # Конвертируем старый формат в новый при запуске
    if os.path.exists(MEMBERS_FILE):
        try:
            with open(MEMBERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Конвертируем старые данные
            members = []
            if isinstance(data, dict) and 'members' in data:
                if isinstance(data['members'], list):
                    for item in data['members']:
                        if isinstance(item, str):
                            members.append({
                                'type': 'username',
                                'value': item
                            })
                        elif isinstance(item, dict):
                            members.append(item)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        members.append({
                            'type': 'username',
                            'value': item
                        })
                    elif isinstance(item, dict):
                        members.append(item)
            elif isinstance(data, dict) and 'users' in data:
                members = data['users']
            
            if members:
                with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({'users': members}, f, ensure_ascii=False, indent=4)
                print(f"✅ Данные сконвертированы ({len(members)} участников)")
        except Exception as e:
            print(f"⚠️ Ошибка при конвертации: {e}")
    else:
        with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'users': []}, f, ensure_ascii=False, indent=4)
        print(f"✅ Создан файл {MEMBERS_FILE}")
    
    print("🚀 Бот запущен!")
    print("📝 Бот отвечает ТОЛЬКО на команды")
    executor.start_polling(dp, skip_updates=True)
