# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - TELEGRAM BOT v3.8 (Survival Update) 🦔
# =====================================
# ЧАСТЬ 1: Импорты, настройки, БД, утилиты

import asyncio
import random
import io
import os
from datetime import datetime, timedelta

import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, 
    InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton,
    BufferedInputFile, FSInputFile, InlineQuery, InlineQueryResultArticle, 
    InputTextMessageContent
)
from aiogram.filters import CommandStart, Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ChatMemberStatus, ButtonStyle

# Попытка импорта Pillow для Image Test
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    print("⚠️ Библиотека Pillow не найдена. Image Test работать не будет.")

# =====================================
# ⚙️ НАСТРОЙКИ - ВСТАВЬ СВОЙ ТОКЕН СЮДА
# =====================================

BOT_TOKEN = "8914077813:AAE77O2UHuSkA9o7hDjozQH5Pg5yIRvWDd8"
MAIN_ADMIN_USERNAME = "Nonametipp"
CHANNEL_ID = -1002483918
CHANNEL_LINK = "https://t.me/+hGOqFr0HoQM3Mjgy"
DB_NAME = os.environ.get("DB_NAME", "hedgehog_bot.db")

# =====================================
# 🎨 ЦВЕТА ИГОЛОК
# =====================================

COLORS = {
    "black": "⚫ Чёрный",
    "brown": "🟤 Коричневый", 
    "white": "⚪ Белый",
    "orange": "🟠 Оранжевый",
    "gold": "🟡 Золотой",
    "blue": "🔵 Синий",
    "purple": "🟣 Фиолетовый",
    "red": "🔴 Красный",
    "green": "🟢 Зелёный",
    "rainbow": "🌈 Радужный"
}

# =====================================
# 💰 МАППИНГ ВАЛЮТ (для отображения)
# =====================================

CURRENCY_LABELS = {
    "balance": "Ежидзиков👍",
    "skin": "Кожи слона🐘",
    "diamonds": "Алмазов💎"
}

# =====================================
# 🤠 КЛАССЫ ЕЖЕЙ (v3.8)
# =====================================

CLASSES = {
    "normal": {"name": "Обычный Еж 🦔", "price": 220, "max_satiety": 100},
    "ejidze": {"name": "Ежидзе 🤠", "price": 350, "max_satiety": 100},
    "fat": {"name": "Толстый Еж 🦔", "price": 300, "max_satiety": 200},
    "golden": {"name": "Золотой Еж 🟡", "price": 600, "max_satiety": 100}
}

# =====================================
# 🎰 НАСТРОЙКИ КАЗИНО
# =====================================

CASINO_EMOJI = ["🦔", "🌟", "🙀", "🎰", "👬", "🛒", "🏅", "😁"]

EJINO_MULTIPLIERS = [
    (0, 18),
    (0.5, 18),
    (1, 18),
    (1.5, 18),
    (2, 20),
    (5, 8)
]

# =====================================
# 🥕 ЕДА (v3.8)
# =====================================

FOOD_ITEMS = [
    ("Тухлое яблоко", 2, 1),
    ("Яблоко", 5, 4),
    ("Груша", 6, 5),
    ("Жук-хрущ", 12, 10),
    ("Молоко кота", 30, 20),
    ("Молоко", 39, 25),
    ("Хлеб", 59, 40),
    ("Капуста", 70, 50),
    ("Электрический робот насыщитель", 111, 100)
    # Ядерка реализована отдельно как недоступный предмет
]

# =====================================
# 🛒 ТОВАРЫ МАГАЗИНА (Базовые)
# =====================================
# Мебель помечается ключевыми словами для механики выживания

DEFAULT_SHOP_ITEMS = [
    ("Стул", 32),
    ("Стол", 35),
    ("Кусок двери", 5),
    ("Дверь", 20),
    ("Тухлый порванный зелёный матрас с мусорки", 0),
    ("Хорошая кровать", 40),
    ("Кровать", 30),
    ("Диван", 60), # New furniture
    ("Телевизовизор", 50),
    ("Телетелевизовизовизор", 70),
    ("ТВ", 100),
    ("Лампочки в пакете", 110),
    ("Часы из меди", 140),
    ("Мягкий ёж", 200),
    ("Серебряная книга", 400),
    ("Дом", 550),
    ("Собственная ракета", 999),
    ("Мини вселенная в банке", 2000),
    ("Супер-консоль >_<", 4500),
    ("Аптечка 🩹", 50)
]

# Список слов, определяющих мебель (для снижения голода)
FURNITURE_KEYWORDS = ["стул", "стол", "дверь", "матрас", "кровать", "диван", "дом"]

# =====================================
# 🗄️ БАЗА ДАННЫХ
# =====================================

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. СОЗДАЕМ ТАБЛИЦЫ
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                player_number INTEGER UNIQUE,
                balance INTEGER DEFAULT 0,
                diamonds INTEGER DEFAULT 0,
                elephant_skin INTEGER DEFAULT 0,
                hedgehog_name TEXT DEFAULT '🦔Ежъ🦔',
                hedgehog_color TEXT DEFAULT 'Не выбран',
                hedgehog_class TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'alive',
                satiety REAL DEFAULT 100.0,
                happiness REAL DEFAULT 0,
                ants INTEGER DEFAULT 0,
                ant_chance REAL DEFAULT 10.0,
                referrer_id INTEGER DEFAULT NULL,
                referrals_count INTEGER DEFAULT 0,
                referrals_earned INTEGER DEFAULT 0,
                total_feedings INTEGER DEFAULT 0,
                join_date TEXT,
                last_daily TEXT DEFAULT NULL,
                last_ant_collect TEXT DEFAULT NULL,
                last_beg TEXT DEFAULT NULL,
                double_ad_until TEXT DEFAULT NULL,
                ad_index INTEGER DEFAULT 0,
                is_injured INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT DEFAULT NULL,
                ban_ads INTEGER DEFAULT 0,
                ban_books INTEGER DEFAULT 0,
                is_fake_admin INTEGER DEFAULT 0,
                alert_sent INTEGER DEFAULT 0,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                total_casino_profit INTEGER DEFAULT 0
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                amount INTEGER DEFAULT 0,
                timestamp TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                reward_type TEXT,
                reward_value TEXT,
                uses_left INTEGER,
                total_uses INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'Unknown',
                created_at TEXT DEFAULT NULL
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS used_promocodes (
                user_id INTEGER,
                code TEXT,
                used_at TEXT DEFAULT NULL,
                PRIMARY KEY (user_id, code)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT PRIMARY KEY,
                added_by TEXT,
                added_at TEXT,
                can_edit_promos INTEGER DEFAULT 0
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS custom_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT UNIQUE,
                response_text TEXT,
                media_type TEXT DEFAULT NULL,
                media_file_id TEXT DEFAULT NULL,
                created_by TEXT,
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                price INTEGER,
                currency TEXT DEFAULT 'balance'
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                quantity INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                UNIQUE(user_id, item_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                message_text TEXT,
                media_type TEXT DEFAULT NULL,
                media_file_id TEXT DEFAULT NULL,
                ticket_type TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_username TEXT,
                action TEXT,
                target_info TEXT,
                timestamp TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS screen_media (
                screen_name TEXT PRIMARY KEY,
                file_id TEXT,
                media_type TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # NEW v3.8 Table for Books
        await db.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER,
                author_username TEXT,
                title TEXT,
                content TEXT,
                price INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        ''')
        
        # 2. МИГРАЦИЯ (ДОБАВЛЕНИЕ КОЛОНОК)
        new_columns = [
            ("users", "player_number", "INTEGER"),
            ("users", "is_injured", "INTEGER DEFAULT 0"),
            ("users", "is_banned", "INTEGER DEFAULT 0"),
            ("users", "ban_reason", "TEXT"),
            ("users", "casino_wins", "INTEGER DEFAULT 0"),
            ("users", "casino_losses", "INTEGER DEFAULT 0"),
            ("users", "total_casino_profit", "INTEGER DEFAULT 0"),
            ("users", "elephant_skin", "INTEGER DEFAULT 0"),
            ("users", "hedgehog_class", "TEXT DEFAULT 'normal'"),
            ("users", "status", "TEXT DEFAULT 'alive'"),
            ("users", "satiety", "REAL DEFAULT 100.0"),
            ("users", "last_beg", "TEXT DEFAULT NULL"),
            ("promocodes", "created_by", "TEXT DEFAULT 'Unknown'"),
            ("promocodes", "created_at", "TEXT"),
            ("shop_items", "currency", "TEXT DEFAULT 'balance'"),
            ("admins", "can_edit_promos", "INTEGER DEFAULT 0"),
            # Survival Update v3.8 Columns
            ("users", "diamonds", "INTEGER DEFAULT 0"),
            ("users", "ban_ads", "INTEGER DEFAULT 0"),
            ("users", "ban_books", "INTEGER DEFAULT 0"),
            ("users", "is_fake_admin", "INTEGER DEFAULT 0"),
            ("users", "alert_sent", "INTEGER DEFAULT 0")
        ]
        
        for table, column, col_type in new_columns:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except:
                pass
        
        await db.commit()

        # 3. ВСТАВКА ДАННЫХ
        await db.execute('''
            INSERT OR IGNORE INTO admins (username, added_by, added_at, can_edit_promos)
            VALUES (?, 'system', ?, 1)
        ''', (MAIN_ADMIN_USERNAME, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Товары
        for name, price in DEFAULT_SHOP_ITEMS:
            await db.execute('INSERT OR IGNORE INTO shop_items (name, price, currency) VALUES (?, ?, "balance")', (name, price))
        
        # Настройки
        default_settings = [
            ("maintenance_mode", "0"),
            ("feed_cost", "150"), # Legacy, but kept in DB
            ("ant_catch_cost", "200"),
            ("ant_income", "10"),
            ("daily_bonus", "25")
        ]
        for key, value in default_settings:
            await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
        
        await db.commit()
        
        # Нумерация игроков
        async with db.execute("SELECT user_id FROM users WHERE player_number IS NULL ORDER BY rowid") as cursor:
            users_without_number = await cursor.fetchall()
        
        if users_without_number:
            async with db.execute("SELECT COALESCE(MAX(player_number), 0) FROM users") as cursor:
                max_num = (await cursor.fetchone())[0]
            
            for i, (uid,) in enumerate(users_without_number, start=max_num + 1):
                await db.execute("UPDATE users SET player_number = ? WHERE user_id = ?", (i, uid))
            await db.commit()
        
        print("✅ База данных инициализирована корректно!")


async def reset_database():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()
        
        tables = ["users", "stats", "promocodes", "used_promocodes", "ads", 
                  "admins", "custom_commands", "shop_items", "inventory", 
                  "support_tickets", "admin_logs", "bot_settings", "screen_media", "books"]
        for table in tables:
            await db.execute(f"DROP TABLE IF EXISTS {table}")
        await db.commit()
    
    await init_db()
    return [u[0] for u in users]


# =====================================
# 🔧 УТИЛИТЫ
# =====================================

async def get_setting(key: str, default: str = "0") -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()


async def add_admin_log(admin_username: str, action: str, target_info: str = ""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO admin_logs (admin_username, action, target_info, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (admin_username, action, target_info, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()

async def get_screen_media(screen_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM screen_media WHERE screen_name = ?", (screen_name,)) as cursor:
            return await cursor.fetchone()

async def set_screen_media(screen_name: str, file_id: str, media_type: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO screen_media (screen_name, file_id, media_type)
            VALUES (?, ?, ?)
        ''', (screen_name, file_id, media_type))
        await db.commit()

async def delete_screen_media(screen_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM screen_media WHERE screen_name = ?", (screen_name,))
        await db.commit()

async def get_next_player_number() -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COALESCE(MAX(player_number), 0) FROM users") as cursor:
            return (await cursor.fetchone())[0] + 1


async def check_maintenance() -> bool:
    return await get_setting("maintenance_mode", "0") == "1"


async def check_user_banned(user_id: int) -> tuple:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT is_banned, ban_reason FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return True, row[1]
            return False, None

async def check_shadow_ban(user_id: int, ban_type: str) -> bool:
    # ban_type: 'ban_ads' or 'ban_books'
    if ban_type not in ("ban_ads", "ban_books"):
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(f"SELECT {ban_type} FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row and row[0] == 1


def format_player_number(num: int) -> str:
    if num:
        return f"#{num:04d}"
    return "#????"


# =====================================
# 👤 ФУНКЦИИ ПОЛЬЗОВАТЕЛЯ
# =====================================

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def create_user(user_id: int, username: str, referrer_id: int = None):
    player_number = await get_next_player_number()
    # Старт с 0, если реферал - 200 (как в ТЗ)
    start_balance = 200 if referrer_id else 0
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, player_number, balance, join_date, referrer_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'alive')
        ''', (user_id, username, player_number, start_balance, join_date, referrer_id))
        
        if referrer_id:
            await db.execute('''
                UPDATE users SET 
                    balance = balance + 20,
                    referrals_count = referrals_count + 1,
                    referrals_earned = referrals_earned + 20,
                    ant_chance = MIN(ant_chance + 0.3, 30.0)
                WHERE user_id = ?
            ''', (referrer_id,))
            
            double_until = (datetime.now() + timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute("UPDATE users SET double_ad_until = ? WHERE user_id = ?", (double_until, referrer_id))
            
            promo_code = f"REF{referrer_id}{random.randint(1000,9999)}"
            await db.execute('''
                INSERT OR IGNORE INTO promocodes (code, reward_type, reward_value, uses_left, created_by, created_at)
                VALUES (?, 'balance', '10', 1, 'system', ?)
            ''', (promo_code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        await db.commit()
    return player_number


async def update_username(user_id: int, new_username: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            old_username = row[0] if row else None

        await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (new_username, user_id))

        if old_username and old_username != new_username:
            try:
                await db.execute("UPDATE admins SET username = ? WHERE username = ?", (new_username, old_username))
            except Exception:
                # UNIQUE constraint — новый username уже есть в admins, просто пропускаем
                pass

        await db.commit()


async def update_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()
    
    if amount > 0:
        await add_stat(user_id, "balance_add", amount)


async def get_balance(user_id: int) -> int:
    user = await get_user(user_id)
    return user['balance'] if user else 0

async def update_elephant_skin(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET elephant_skin = elephant_skin + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_elephant_skin(user_id: int) -> int:
    user = await get_user(user_id)
    return user['elephant_skin'] if user else 0


async def add_stat(user_id: int, action_type: str, amount: int = 0):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO stats (user_id, action_type, amount, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (user_id, action_type, amount, timestamp))
        await db.commit()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            return [u[0] for u in await cursor.fetchall()]


async def find_user_flexible(search_input: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        if search_input.startswith("#"):
            try:
                number = int(search_input[1:])
                async with db.execute("SELECT * FROM users WHERE player_number = ?", (number,)) as cursor:
                    return await cursor.fetchone()
            except:
                pass
        
        if search_input.startswith("@"):
            async with db.execute("SELECT * FROM users WHERE username = ?", (search_input[1:],)) as cursor:
                return await cursor.fetchone()
        
        try:
            user_id = int(search_input)
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                return await cursor.fetchone()
        except:
            pass
        
        async with db.execute("SELECT * FROM users WHERE username = ?", (search_input,)) as cursor:
            return await cursor.fetchone()


# =====================================
# 👑 ФУНКЦИИ АДМИНОВ
# =====================================

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            username = row[0]
        
        async with db.execute("SELECT * FROM admins WHERE username = ?", (username,)) as cursor:
            return await cursor.fetchone() is not None

async def is_fake_admin(user_id: int) -> bool:
    user = await get_user(user_id)
    return user and user['is_fake_admin'] == 1

async def can_edit_promos(user_id: int) -> bool:
    if await is_main_admin(user_id):
        return True
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return False
            username = row[0]
        async with db.execute("SELECT can_edit_promos FROM admins WHERE username = ?", (username,)) as cursor:
            res = await cursor.fetchone()
            return res and res[0] == 1

async def is_main_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row and row[0] == MAIN_ADMIN_USERNAME


async def get_all_admins():
    async with aiosqlite.connect(DB_NAME) as db:
        result = []
        async with db.execute("SELECT username, added_by, added_at, can_edit_promos FROM admins") as cursor:
            admins = await cursor.fetchall()
        
        for admin in admins:
            async with db.execute("SELECT user_id FROM users WHERE username = ?", (admin[0],)) as cursor:
                user_row = await cursor.fetchone()
                uid = user_row[0] if user_row else None
            
            result.append({
                'user_id': uid,
                'username': admin[0],
                'added_by': admin[1],
                'added_at': admin[2],
                'can_edit_promos': admin[3]
            })
        
        return result


async def add_admin(username: str, added_by: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO admins (username, added_by, added_at, can_edit_promos)
            VALUES (?, ?, ?, 0)
        ''', (username, added_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()


async def remove_admin(username: str):
    if username == MAIN_ADMIN_USERNAME:
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM admins WHERE username = ?", (username,))
        await db.commit()
    return True


async def ensure_main_admin(username: str):
    if username == MAIN_ADMIN_USERNAME:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT * FROM admins WHERE username = ?", (MAIN_ADMIN_USERNAME,)) as cursor:
                if not await cursor.fetchone():
                    await db.execute('''
                        INSERT OR IGNORE INTO admins (username, added_by, added_at, can_edit_promos)
                        VALUES (?, 'system', ?, 1)
                    ''', (MAIN_ADMIN_USERNAME, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    await db.commit()


# =====================================
# 📢 ПРОВЕРКА ПОДПИСКИ
# =====================================

_subscription_cache: dict[int, tuple[bool, datetime]] = {}
_SUB_CACHE_TTL = timedelta(minutes=5)

async def check_subscription(bot_instance: Bot, user_id: int) -> bool:
    now = datetime.now()
    cached = _subscription_cache.get(user_id)
    if cached:
        value, cached_time = cached
        if now - cached_time < _SUB_CACHE_TTL:
            return value
    try:
        member = await bot_instance.get_chat_member(CHANNEL_ID, user_id)
        result = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except:
        result = True
    _subscription_cache[user_id] = (result, now)
    return result


# =====================================
# 📢 РАССЫЛКА
# =====================================

async def broadcast_message(bot_instance: Bot, user_ids: list, text: str = None, photo_id: str = None, video_id: str = None):
    success = failed = 0
    for user_id in user_ids:
        try:
            if photo_id:
                await bot_instance.send_photo(user_id, photo_id, caption=text)
            elif video_id:
                await bot_instance.send_video(user_id, video_id, caption=text)
            elif text:
                await bot_instance.send_message(user_id, text)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    return success, failed


# =====================================
# 🤖 ИНИЦИАЛИЗАЦИЯ БОТА
# =====================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Автоматический callback.answer() через middleware — убирает "часики" на кнопках
class AutoAnswerMiddleware:
    async def __call__(self, handler, event, data):
        try:
            result = await handler(event, data)
        finally:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer()
                except:
                    pass
        return result

router.callback_query.middleware(AutoAnswerMiddleware())

dp.include_router(router)


# =====================================
# 📋 СОСТОЯНИЯ FSM
# =====================================

class UserStates(StatesGroup):
    waiting_name = State()
    waiting_ad_photo = State()
    waiting_support_message = State()
    waiting_suggestion_message = State()
    casino_bet = State()
    dice_numbers = State()
    star_game = State()
    image_test_text = State()
    transfer_user = State()
    transfer_amount = State()
    custom_bet_amount = State()
    # Books FSM
    book_title = State()
    book_text = State()
    book_price = State()

class AdminStates(StatesGroup):
    waiting_promo_code = State()
    waiting_promo_type = State()
    waiting_promo_value = State()
    waiting_promo_uses = State()
    waiting_user_search = State()
    waiting_amount = State()
    waiting_command_name = State()
    waiting_command_response = State()
    waiting_admin_username = State()
    waiting_support_reply = State()
    waiting_item_name = State()
    waiting_item_price = State()
    waiting_item_currency = State()
    waiting_inventory_user = State()
    waiting_broadcast_message = State()
    waiting_ban_reason = State()
    waiting_global_gift = State()
    waiting_personal_message = State()
    waiting_setting_value = State()
    waiting_add_screen_name = State()
    waiting_add_media = State()
    # Fake Admin FSM
    waiting_fake_admin_search = State()

# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - ЧАСТЬ 2/5 🦔
# =====================================
# Клавиатуры

# =====================================
# ⌨️ REPLY КЛАВИАТУРА (внизу экрана)
# =====================================

def main_reply_keyboard(is_admin: bool = False, is_fake_admin: bool = False):
    buttons = [
        [KeyboardButton(text="🏠 Меню", style=ButtonStyle.PRIMARY)],
        [KeyboardButton(text="🦔 Мой Ёж"), KeyboardButton(text="🌟 Финансы")],
        [KeyboardButton(text="🤔 Поддержка"), KeyboardButton(text="🎰 Ежино")],
        [KeyboardButton(text="Image Test")]
    ]
    if is_admin or is_fake_admin:
        buttons.append([KeyboardButton(text="🛠 Панель", style=ButtonStyle.DANGER)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def death_reply_keyboard():
    # Удалена кнопка Рекламы для хардкора в Survival Update
    buttons = [
        [KeyboardButton(text="🏠 Меню", style=ButtonStyle.PRIMARY)],
        [KeyboardButton(text="🔘 Получить 1 ежидзик за клик 😢")],
        [KeyboardButton(text="🙏 Попросить Денег")],
        [KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="🆕 Купить Ежа", style=ButtonStyle.SUCCESS)],
        [KeyboardButton(text="🧪 Dev Test", style=ButtonStyle.DANGER)]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# =====================================
# ⌨️ INLINE КЛАВИАТУРЫ
# =====================================

def subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Подписаться", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription", style=ButtonStyle.SUCCESS)]
    ])


def main_menu_keyboard(is_admin: bool = False):
    # Обновленный дизайн для Survival v3.8
    buttons = [
        [
            InlineKeyboardButton(text="🦔Покормить🦔", callback_data="feed", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text="🦔Погладить🦔", callback_data="pet", style=ButtonStyle.SUCCESS)
        ],
        [
            InlineKeyboardButton(text="🛒Магазин🛒", callback_data="shop"),
            InlineKeyboardButton(text="⚒️ Кузница", callback_data="stub_forge") # STUB
        ],
        [
             InlineKeyboardButton(text="💎 Алмазы", callback_data="diamond_menu"), # NEW
             InlineKeyboardButton(text="🤖 ИИ-ЕЖ", callback_data="stub_ai") # STUB
        ],
        [
            InlineKeyboardButton(text="💸 Перевод", callback_data="transfer_menu"),
            InlineKeyboardButton(text="♻️ Обменник", callback_data="exchange")
        ],
        [
            InlineKeyboardButton(text="🌐 Сайт", callback_data="website"),
             InlineKeyboardButton(text="📞 Звонок", callback_data="call"),
        ],
        [
            InlineKeyboardButton(text="👬Пригласить друга👬", callback_data="invite"),
            InlineKeyboardButton(text="🎁Бонусы🎁", callback_data="bonuses", style=ButtonStyle.PRIMARY)
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛠 Панель", callback_data="admin_panel", style=ButtonStyle.DANGER)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_button(callback_data: str = "menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data=callback_data)]
    ])


def feed_keyboard():
    buttons = []
    # Generate buttons from FOOD_ITEMS
    for idx, (name, price, sati) in enumerate(FOOD_ITEMS):
        buttons.append([InlineKeyboardButton(text=f"{name} ({price}💰) +{sati}%", callback_data=f"feed_item_{idx}")])
    
    buttons.append([InlineKeyboardButton(text="☢️ Ядерка (♾️)", callback_data="noop", style=ButtonStyle.DANGER)])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pet_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Погладить 🦔", callback_data="do_pet")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])


def injured_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 В магазин!", callback_data="shop")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])


def my_hedgehog_keyboard(h_class: str):
    buttons = [
        [InlineKeyboardButton(text="🖌️Кастомизировать", callback_data="customize", style=ButtonStyle.PRIMARY)]
    ]
    if h_class == 'normal':
        buttons.append([InlineKeyboardButton(text="🤝 Отдать ёжика на хранение", callback_data="store_hedgehog")])
    else:
        buttons.append([InlineKeyboardButton(text="💸 Продать Ежа", callback_data="sell_hedgehog", style=ButtonStyle.DANGER)])
        
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
                  )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def customize_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить имя (бесплатно)", callback_data="change_name")],
        [InlineKeyboardButton(text="🎨 Изменить цвет (100 Ежидзиков👍)", callback_data="change_color")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="my_hedgehog")]
    ])


def colors_keyboard():
    buttons = []
    color_items = list(COLORS.items())
    for i in range(0, len(color_items), 2):
        row = [InlineKeyboardButton(text=color_items[i][1], callback_data=f"color_{color_items[i][0]}")]
        if i + 1 < len(color_items):
            row.append(InlineKeyboardButton(text=color_items[i+1][1], callback_data=f"color_{color_items[i+1][0]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="customize")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def finances_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 Топ по ежидзикам👍", callback_data="top_balance"),
            InlineKeyboardButton(text="🏆 Топ по коже слона🐘", callback_data="top_skin")
        ],
        [
            InlineKeyboardButton(text="🏆 Топ по кормлениям+", callback_data="top_feedings_period"),
            InlineKeyboardButton(text="🏆 Топ по кормлениям (всё время)", callback_data="top_feedings_all")
        ],
        [InlineKeyboardButton(text="🏆 Топ по рефералам", callback_data="top_referrals")],
        [InlineKeyboardButton(text="🐜 Муравьишки!", callback_data="ants")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])


def top_period_keyboard(top_type: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="За всё время", callback_data=f"{top_type}_all"),
            InlineKeyboardButton(text="За месяц", callback_data=f"{top_type}_month")
        ],
        [
            InlineKeyboardButton(text="За неделю", callback_data=f"{top_type}_week"),
            InlineKeyboardButton(text="За день", callback_data=f"{top_type}_day")
        ],
        [InlineKeyboardButton(text="За час", callback_data=f"{top_type}_hour")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="finances")]
    ])


def ants_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐜 Попытка - не пытка 🐜", callback_data="catch_ant")],
        [InlineKeyboardButton(text="⚙️ Управление муравьями", callback_data="manage_ants")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="finances")]
    ])


def manage_ants_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Удалить муравья", callback_data="delete_ant")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="ants")]
    ])


def bonuses_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📺 Смотреть рекламу", callback_data="watch_ad"),
            InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily_bonus")
        ],
        [InlineKeyboardButton(text="📤 Выставить рекламу (70 Ежидзиков👍)", callback_data="submit_ad")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])

def support_keyboard(is_main_admin: bool = False):
    buttons = [
        [
            InlineKeyboardButton(text="🆘 Написать в техподдержку", callback_data="write_support", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text="💫 Предложить обновление", callback_data="write_suggestion")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Inline режим", callback_data="support_inline_info"),
        ],
        [
            InlineKeyboardButton(text="📜 Политика использования", callback_data="policy_usage"),
            InlineKeyboardButton(text="🔒 Политика конфиденциальности", callback_data="policy_privacy")
        ],
        [InlineKeyboardButton(text="🔄 Ресет username", callback_data="reset_username")]
    ]
    if is_main_admin:
        buttons.append([InlineKeyboardButton(text="☢️ СУПЕР ОЧИСТКА ☢️", callback_data="super_reset", style=ButtonStyle.DANGER)])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
                  )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def shop_keyboard(is_admin: bool = False):
    buttons = [
        [
            InlineKeyboardButton(text="📋 Список товаров", callback_data="shop_list"),
            InlineKeyboardButton(text="📚 Библиотека / Книги", callback_data="book_menu")
        ],
        [InlineKeyboardButton(text="👾 Инвентарь", callback_data="inventory")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛒 Товыры (Админ)", callback_data="admin_shop")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def shop_item_keyboard(item_index: int, total_items: int):
    buttons = []
    nav_buttons = []
    
    if total_items > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"shop_item_{(item_index - 1) % total_items}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{item_index + 1}/{total_items}", callback_data="noop"))
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"shop_item_{(item_index + 1) % total_items}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="💰 Купить", callback_data=f"buy_item_{item_index}", style=ButtonStyle.SUCCESS)])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def inventory_keyboard(item_index: int, total_items: int, item_name: str = "", is_injured: bool = False):
    buttons = []
    nav_buttons = []
    
    if total_items > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"inv_item_{(item_index - 1) % total_items}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{item_index + 1}/{total_items}", callback_data="noop"))
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"inv_item_{(item_index + 1) % total_items}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    if "Аптечка" in item_name and is_injured:
        buttons.append([InlineKeyboardButton(text="💊 Вылечить руку", callback_data=f"heal_hand_{item_index}")])
    
    buttons.append([InlineKeyboardButton(text="💸 Продать", callback_data=f"sell_item_{item_index}")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sell_confirm_keyboard(item_index: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, продать", callback_data=f"confirm_sell_{item_index}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"inv_item_{item_index}")
        ]
    ])

def exchange_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 45 Еж. -> 1 Кожа", callback_data="do_exchange_to_skin")],
        [InlineKeyboardButton(text="🔄 1 Кожа -> 45 Еж.", callback_data="do_exchange_to_balance")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])

def diamond_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 Обмен: 3 Кожи -> 1 Алмаз", callback_data="ex_skin_to_dia"),
            InlineKeyboardButton(text="🐘 Обмен: 1 Алмаз -> 3 Кожи", callback_data="ex_dia_to_skin")
        ],
        [InlineKeyboardButton(text="🏆 Топ богачей (Алмазы)", callback_data="top_diamonds")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])

def transfer_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Начать перевод", callback_data="start_transfer")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])

def image_test_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_image_test")]
    ])

def class_select_keyboard():
    buttons = []
    for cls_key, cls_data in CLASSES.items():
        style = ButtonStyle.SUCCESS if cls_key == 'normal' else ButtonStyle.PRIMARY
        buttons.append([InlineKeyboardButton(text=f"{cls_data['name']} - {cls_data['price']} Еж.", callback_data=f"buy_class_{cls_key}", style=style)])
    buttons.append([InlineKeyboardButton(text="Назад в посмертие", callback_data="death_menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def book_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать книгу", callback_data="write_book", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text="📚 Магазин книг", callback_data="buy_books")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="shop")]
    ])

def book_buy_keyboard(book_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Купить книгу", callback_data="purchase_book_" + str(book_id), style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="buy_books")]
    ])

def book_mod_keyboard(book_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_book_{book_id}", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_book_{book_id}", style=ButtonStyle.DANGER)]
    ])

# =====================================
# 🎰 КАЗИНО КЛАВИАТУРЫ
# =====================================

def casino_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 Бросить кубик", callback_data="casino_dice"),
            InlineKeyboardButton(text="🦔 Ежино", callback_data="casino_ejino")
        ],
        [
            InlineKeyboardButton(text="🎰 Сл0ти|<И", callback_data="casino_slots"),
            InlineKeyboardButton(text="🌟 Найди звезду", callback_data="casino_star")
        ],
        [InlineKeyboardButton(text="☠️ ×10 от ставки", callback_data="casino_x10", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])


def casino_bet_keyboard(game_type: str):
    buttons = [
        [
            InlineKeyboardButton(text="10", callback_data=f"bet_{game_type}_10"),
            InlineKeyboardButton(text="50", callback_data=f"bet_{game_type}_50"),
            InlineKeyboardButton(text="100", callback_data=f"bet_{game_type}_100")
        ],
        [
            InlineKeyboardButton(text="250", callback_data=f"bet_{game_type}_250"),
            InlineKeyboardButton(text="500", callback_data=f"bet_{game_type}_500"),
            InlineKeyboardButton(text="1000", callback_data=f"bet_{game_type}_1000")
        ],
        [InlineKeyboardButton(text="🖊 Своя ставка", callback_data=f"bet_{game_type}_custom")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="casino")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dice_numbers_keyboard(selected: list):
    buttons = []
    for row_start in [1, 4]:
        row = []
        for num in range(row_start, row_start + 3):
            if num in selected:
                row.append(InlineKeyboardButton(text=f"✅ {num}", callback_data=f"dice_num_{num}"))
            else:
                row.append(InlineKeyboardButton(text=str(num), callback_data=f"dice_num_{num}"))
        buttons.append(row)
    
    if len(selected) == 3:
        buttons.append([InlineKeyboardButton(text="🎲 Бросить кубик!", callback_data="dice_roll")])
    else:
        buttons.append([InlineKeyboardButton(text=f"Выбрано: {len(selected)}/3", callback_data="noop")])
    
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="casino")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def slots_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить!", callback_data="slots_spin")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="casino")]
    ])


def ejino_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦔 Крутить Ежино!", callback_data="ejino_spin")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="casino")]
    ])


def star_field_keyboard(field: list, revealed: list):
    buttons = []
    for row in range(5):
        row_buttons = []
        for col in range(5):
            idx = row * 5 + col
            if idx in revealed:
                if field[idx] == "⭐":
                    row_buttons.append(InlineKeyboardButton(text="🌟", callback_data="noop"))
                else:
                    row_buttons.append(InlineKeyboardButton(text="❌", callback_data="noop"))
            else:
                row_buttons.append(InlineKeyboardButton(text="❓", callback_data=f"star_{idx}"))
        buttons.append(row_buttons)
    buttons.append([InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data="star_end"), InlineKeyboardButton(text="❌ Отмена", callback_data="casino")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def x10_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☠️ РИСКНУТЬ!", callback_data="x10_try", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="casino")]
    ])


# =====================================
# 🛠 АДМИН КЛАВИАТУРЫ (AdminOS v3.8)
# =====================================

def admin_os_login_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Войти в систему", callback_data="admin_login_verify", style=ButtonStyle.PRIMARY)]
    ])

def fake_admin_keyboard():
    # Фейковый вход, ведет на стикеры
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Войти в систему", url="https://t.me/addstickers/totallynormalstickerpackk_by_fStikBot")]
    ])

def admin_main_keyboard():
    # AdminOS Dashboard
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Игроки", callback_data="admin_folder_players"),
            InlineKeyboardButton(text="📢 Маркетинг", callback_data="admin_folder_marketing")
        ],
        [
            InlineKeyboardButton(text="🛒 Контент", callback_data="admin_folder_content"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_folder_settings")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📜 Логи", callback_data="admin_logs")
        ],
        [InlineKeyboardButton(text="🔴 Выход", callback_data="menu", style=ButtonStyle.DANGER)]
    ])

def admin_players_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Поиск / Действия", callback_data="admin_manage_balance", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text="🚫 Бан-лист", callback_data="admin_banlist", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="🤡 Фейк Админы", callback_data="admin_manage_fakes")],
        [InlineKeyboardButton(text="✉️ Личное сообщение", callback_data="admin_personal_msg")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

def admin_marketing_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="🎟 Все промокоды", callback_data="admin_all_promos")],
        [InlineKeyboardButton(text="🖼 Модерация рекламы", callback_data="admin_moderate_ads")],
        [InlineKeyboardButton(text="🗑 Удалить рекламу", callback_data="admin_delete_ads", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="🎁 Подарок всем", callback_data="admin_global_gift", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

def admin_content_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Управление товарами", callback_data="admin_shop")],
        [InlineKeyboardButton(text="📝 Команды", callback_data="admin_manage_commands")],
        [InlineKeyboardButton(text="➕ Добавить команду", callback_data="admin_add_command", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="🖼 Медиа (/add)", callback_data="admin_manage_media")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

def admin_settings_keyboard(is_main: bool):
    buttons = [
        [InlineKeyboardButton(text="🔧 Тех. работы", callback_data="admin_maintenance", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="⚙️ Игровые цены", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📥 Скачать БД", callback_data="admin_download_db")]
    ]
    if is_main:
        buttons.append([InlineKeyboardButton(text="👑 Управление админами", callback_data="admin_manage_admins")])
        buttons.append([InlineKeyboardButton(text="☢️ SUPER RESET", callback_data="super_reset", style=ButtonStyle.DANGER)])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def fake_admin_manage_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить Фейка", callback_data="admin_add_fake")],
        [InlineKeyboardButton(text="➖ Удалить Фейка", callback_data="admin_remove_fake")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_folder_players")]
    ])

def player_actions_keyboard(user_id: int):
    # Действия с конкретным игроком после поиска
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Баланс", callback_data=f"act_bal_{user_id}")],
        [InlineKeyboardButton(text="🚫 Бан", callback_data=f"act_ban_{user_id}")],
        [InlineKeyboardButton(text="👻 Теневой бан (Ads)", callback_data=f"act_sban_ads_{user_id}")],
        [InlineKeyboardButton(text="👻 Теневой бан (Books)", callback_data=f"act_sban_books_{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_folder_players")]
    ])

def broadcast_percent_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 100% (Все)", callback_data="broadcast_100"),
            InlineKeyboardButton(text="📢 50%", callback_data="broadcast_50")
        ],
        [
            InlineKeyboardButton(text="📢 25%", callback_data="broadcast_25"),
            InlineKeyboardButton(text="📢 10%", callback_data="broadcast_10")
        ],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_marketing")]
    ])


def admin_shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_item"),
            InlineKeyboardButton(text="🗑 Удалить товар", callback_data="admin_delete_item")
        ],
        [InlineKeyboardButton(text="👀 Посмотреть инвентарь игрока", callback_data="admin_view_inventory")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_content")]
    ])

def shop_currency_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Ежидзики", callback_data="shop_curr_balance"),
            InlineKeyboardButton(text="🐘 Кожа слона", callback_data="shop_curr_skin")
        ],
        [
            InlineKeyboardButton(text="💎 Алмазы", callback_data="shop_curr_diamonds")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_shop")]
    ])


def admin_manage_admins_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin"),
            InlineKeyboardButton(text="➖ Убрать админа", callback_data="admin_remove_admin")
        ],
        [InlineKeyboardButton(text="📋 Список админов", callback_data="admin_list_admins")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_settings")]
    ])


def promo_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Ежидзики", callback_data="promo_type_balance"),
            InlineKeyboardButton(text="🐜 Муравьи", callback_data="promo_type_ants")
        ],
        [InlineKeyboardButton(text="🎨 Цвет иголок", callback_data="promo_type_color")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_marketing")]
    ])


def ad_moderation_keyboard(ad_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_ad_{ad_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_ad_{ad_id}")
        ]
    ])


def support_ticket_keyboard(ticket_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_ticket_{ticket_id}"),
            InlineKeyboardButton(text="🚫 Игнор", callback_data=f"ignore_ticket_{ticket_id}")
        ]
    ])


def confirm_super_reset_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☢️ ДА, УДАЛИТЬ ВСЁ!", callback_data="confirm_super_reset")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="support")]
    ])


def user_search_type_keyboard(action: str):
    # Generic user search
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🆔 По ID", callback_data=f"search_{action}_id"),
            InlineKeyboardButton(text="👤 По @username", callback_data=f"search_{action}_username")
        ],
        [InlineKeyboardButton(text="#️⃣ По номеру игрока", callback_data=f"search_{action}_number")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_players")]
    ])


def promo_list_keyboard(page: int, total_pages: int):
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"promo_page_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"promo_page_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_marketing")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🥕 Цена кормления", callback_data="setting_feed_cost"),
            InlineKeyboardButton(text="🐜 Цена муравья", callback_data="setting_ant_catch_cost")
        ],
        [
            InlineKeyboardButton(text="💰 Доход муравья", callback_data="setting_ant_income"),
            InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="setting_daily_bonus")
        ],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_settings")]
    ])


def ban_user_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_user_{user_id}")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_banlist")]
    ])


def unban_user_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Разбанить", callback_data=f"unban_user_{user_id}")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_banlist")]
    ])


def banlist_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Забанить игрока", callback_data="admin_ban_user"),
            InlineKeyboardButton(text="✅ Разбанить игрока", callback_data="admin_unban_user")
        ],
        [InlineKeyboardButton(text="📋 Список забаненных", callback_data="admin_banned_list")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_players")]
    ])


def maintenance_keyboard(is_on: bool):
    status = "🟢 ВКЛ" if is_on else "🔴 ВЫКЛ"
    toggle = "выключить" if is_on else "включить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Сейчас: {status} | Нажми чтобы {toggle}", callback_data="toggle_maintenance")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_settings")]
    ])


# =====================================
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =====================================

async def safe_edit_text(message: Message, text: str, reply_markup=None, parse_mode=None, media_screen: str = None):
    # Если передан media_screen, пытаемся найти медиа
    if media_screen:
        media_info = await get_screen_media(media_screen)
        if media_info:
            file_id = media_info['file_id']
            media_type = media_info['media_type']
            try:
                # Пытаемся удалить старое сообщение и отправить новое с фото
                await message.delete()
            except:
                pass
            
            try:
                if media_type == 'photo':
                    await message.answer_photo(file_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                    return
                elif media_type == 'video':
                    await message.answer_video(file_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                    return
            except:
                pass  # Медиа не отправилось — падаем на текстовый fallback
    
    # Обычное поведение
    try:
        if message.photo or message.video:
             # Если сообщение было медиа, а новое текст - удаляем и шлем новое
            await message.delete()
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        try:
            await message.delete()
        except:
            pass
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


async def safe_delete(message: Message):
    try:
        await message.delete()
    except:
        pass


async def check_access(bot_instance: Bot, user_id: int, callback: CallbackQuery = None, message: Message = None) -> bool:
    is_banned, ban_reason = await check_user_banned(user_id)
    if is_banned:
        text = f"🚫 Вы заблокированы!\n\nПричина: {ban_reason or 'Не указана'}"
        if callback:
            await callback.answer(text, show_alert=True)
        elif message:
            await message.answer(text)
        return False
    
    # Получаем пользователя для проверки статуса
    user = await get_user(user_id)
    if not user:
        text = "❌ Нажмите /start сначала!"
        if callback:
            await callback.answer(text, show_alert=True)
        elif message:
            await message.answer(text)
        return False
    if user['status'] != 'alive':
        # Если мертв/продан/на хранении
        # Разрешаем только админам доступ к админке, остальным - только "Посмертие"
        
        is_death_action = callback and (
            callback.data in ["watch_ad_death", "death_menu_back"] or 
            callback.data.startswith("buy_class_")
        )
        is_admin_action = callback and callback.data.startswith("admin_") and await is_admin(user_id)
        
        if is_death_action or is_admin_action:
            return True
            
        # Если это сообщение с текстом кнопок смерти
        is_death_text = message and message.text in [
            "🔘 Получить 1 ежидзик за клик 😢", 
            "🙏 Попросить Денег", 
            "💰 Баланс", 
            "🆕 Купить Ежа",
            "🧪 Dev Test",
            "🛠 Панель"
        ]
        
        if is_death_text:
            return True
            
        # Иначе блокируем и шлем меню смерти
        text = "☠️ Ваш ёж мёртв, продан или на хранении.\nМеню недоступно."
        if callback:
            await callback.answer(text, show_alert=True)
            # Отправляем меню смерти если его нет
            await callback.message.answer("🪦 Вы в посмертии...", reply_markup=death_reply_keyboard())
        elif message:
            await message.answer("🪦 Вы в посмертии...", reply_markup=death_reply_keyboard())
        return False

    if await check_maintenance() and not await is_admin(user_id):
        text = "🔧 Ведутся технические работы!\n\nПопробуйте позже."
        if callback:
            await callback.answer(text, show_alert=True)
        elif message:
            await message.answer(text)
        return False
    
    return True

# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - ЧАСТЬ 3/5 🦔
# =====================================
# Основные обработчики

# =====================================
# 🚀 СТАРТ И МЕНЮ
# =====================================

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    is_banned, ban_reason = await check_user_banned(user_id)
    if is_banned:
        await message.answer(f"🚫 Вы заблокированы!\n\nПричина: {ban_reason or 'Не указана'}")
        return
    
    if await check_maintenance() and not await is_admin(user_id):
        await message.answer("🔧 Ведутся технические работы!\n\nПопробуйте позже.")
        return
    
    try:
        await update_username(user_id, username)
    except Exception:
        pass
    try:
        await ensure_main_admin(username)
    except Exception:
        pass
    
    # Обработка рефералов и диплинков
    args = command.args
    referrer_id = None
    promo_to_activate = None
    
    if args:
        if args.startswith("promo_"):
            promo_to_activate = args.replace("promo_", "")
        else:
            try:
                referrer_id = int(args)
                if referrer_id == user_id:
                    referrer_id = None
            except:
                pass
    
    user = await get_user(user_id)
    if not user:
        player_num = await create_user(user_id, username, referrer_id)
        if referrer_id:
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 По вашей ссылке зарегистрировался новый пользователь!\n"
                    f"💰 +20 Ежидзиков👍\n"
                    f"🐜 +0.3% к шансу поймать муравья\n"
                    f"📺 х2 доход с рекламы на 20 минут!"
                )
            except:
                pass
        user = await get_user(user_id)
    
    if not user:
        await message.answer("❌ Ошибка регистрации. Попробуйте ещё раз.")
        return

    # Авто-активация промо из диплинка
    if promo_to_activate:
        pass # Обработаем ниже

    is_user_admin = await is_admin(user_id)
    is_fake = await is_fake_admin(user_id)
    
    # Проверка статуса (v3.8)
    if user['status'] != 'alive':
        await message.answer("🪦 Вы в посмертии...", reply_markup=death_reply_keyboard())
        if promo_to_activate:
             await process_promocode(message, user_id, promo_to_activate)
        return

    # Отправляем reply-клавиатуру и inline-меню
    try:
        text = f"Привет! 👋🦔\nТвой номер игрока: {format_player_number(user['player_number'])}"
        await message.answer(text, reply_markup=main_reply_keyboard(is_user_admin, is_fake))
        await message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
    except Exception as e:
        print(f"❌ Ошибка показа меню в cmd_start: {e}")
        try:
            await message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
        except:
            pass
        
    if promo_to_activate:
        await process_promocode(message, user_id, promo_to_activate)


@router.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    username = callback.from_user.username or "Unknown"
    
    await update_username(user_id, username)
    
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, username)
        user = await get_user(user_id)
    
    is_user_admin = await is_admin(user_id)
    
    if user['status'] != 'alive':
         await callback.message.answer("🪦 Вы в посмертии...", reply_markup=death_reply_keyboard())
         return

    await safe_edit_text(
        callback.message,
        f"Привет! 👋🦔\nТвой номер игрока: {format_player_number(user['player_number'])}\nВот меню бота:",
        reply_markup=main_menu_keyboard(is_user_admin),
        media_screen="menu"
    )


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    try:
        await update_username(callback.from_user.id, callback.from_user.username or "Unknown")
    except Exception:
        pass
    is_user_admin = await is_admin(callback.from_user.id)
    
    try:
        await safe_edit_text(
            callback.message,
            "Привет! 👋🦔\nВот меню бота:",
            reply_markup=main_menu_keyboard(is_user_admin),
            media_screen="menu"
        )
    except Exception:
        try:
            await callback.message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
        except:
            pass


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# =====================================
# 🪦 МЕНЮ ПОСМЕРТИЯ (v3.8)
# =====================================

@router.message(F.text == "🔘 Получить 1 ежидзик за клик 😢")
async def death_clicker(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    if user['status'] == 'alive':
        await message.answer("Ты жив! Зачем тебе это?", reply_markup=main_reply_keyboard(await is_admin(message.from_user.id), await is_fake_admin(message.from_user.id)))
        return

    chance = random.choice([True, False])
    if chance:
        await update_balance(message.from_user.id, 1)
        await message.answer("🔔 +1 Ежидзик👍")
    else:
        await message.answer("🔔 Пусто...")

@router.message(F.text == "🙏 Попросить Денег")
async def death_beg(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    if user['status'] == 'alive': return

    last_beg = user['last_beg']
    now = datetime.now()
    
    if last_beg:
        last_dt = datetime.strptime(last_beg, "%Y-%m-%d %H:%M:%S")
        diff = now - last_dt
        if diff.total_seconds() < 300: # 5 minutes
            remain = 300 - int(diff.total_seconds())
            await message.answer(f"⏳ Подожди еще {remain} секунд...")
            return

    amount = random.randint(20, 69)
    await update_balance(user_id, amount)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET last_beg = ? WHERE user_id = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), user_id))
        await db.commit()
    
    await message.answer(f"🙏 Добрый прохожий дал тебе {amount} Ежидзиков👍")

@router.message(F.text == "💰 Баланс")
async def death_balance(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    if user['status'] == 'alive': return
    await message.answer(f"💰 {user['balance']} Ежидзиков👍")


@router.message(F.text == "🆕 Купить Ежа")
async def death_buy_menu(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    if user['status'] == 'alive': return
    
    await message.answer(
        "🆕 Выбери нового ежа:",
        reply_markup=class_select_keyboard()
    )

@router.callback_query(F.data.startswith("buy_class_"))
async def process_buy_class(callback: CallbackQuery):
    cls_key = callback.data.replace("buy_class_", "")
    cls_data = CLASSES.get(cls_key)
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    if not cls_data: return
    
    if user['status'] == 'alive':
        await callback.answer("❌ У вас уже есть ёжик!", show_alert=True)
        return

    if user['balance'] < cls_data['price']:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return

    # Logic for descriptions
    prev_status = user['status']
    desc_text = ""
    if cls_key == 'normal':
        if prev_status == 'dead':
            desc_text = "Ёжик придёт к вам с небес и приласкается к вам..."
        elif prev_status == 'stored':
             desc_text = "Ваш ёж настолько понравился администраторам хранения ежей, что они решили оставить его себе, а с вас требуют плату 😲"
    else:
        # Show bonuses
        if cls_key == 'ejidze': desc_text = "Бонусы: +10% к муравьям, +5% шанс уколоться."
        elif cls_key == 'fat': desc_text = "Бонусы: 200% сытости."
        elif cls_key == 'golden': desc_text = "Бонусы: x2 реклама, +50 еж. за глажку, авторские отчисления."

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            UPDATE users SET 
                balance = balance - ?,
                hedgehog_color = 'Не выбран',
                hedgehog_class = ?,
                happiness = 0,
                satiety = ?,
                status = 'alive',
                alert_sent = 0
            WHERE user_id = ?
        ''', (cls_data['price'], cls_key, cls_data['max_satiety'], user_id))
        await db.commit()
    
    await callback.message.delete()
    is_user_admin = await is_admin(user_id)
    is_fake = await is_fake_admin(user_id)
    await callback.message.answer(
        f"✅ Вы купили: {cls_data['name']}!\n\n{desc_text}\n\nТеперь вы снова в игре!",
        reply_markup=main_reply_keyboard(is_user_admin, is_fake)
    )
    await callback.message.answer("Меню:", reply_markup=main_menu_keyboard(is_user_admin))

@router.callback_query(F.data == "death_menu_back")
async def death_menu_back(callback: CallbackQuery):
    await safe_delete(callback.message)
    await callback.message.answer("🪦 Вы в посмертии...", reply_markup=death_reply_keyboard())

@router.message(F.text == "🧪 Dev Test")
async def death_dev_test(message: Message):
    """Dev Test: бесплатно покупает обычного ежа с 100% сытостью, даже если нет средств"""
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    if user['status'] == 'alive':
        await message.answer("❌ У вас уже есть ёжик!")
        return

    # Бесплатно даём обычного ежа с 100% сытости
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            UPDATE users SET
                hedgehog_color = 'Не выбран',
                hedgehog_class = 'normal',
                happiness = 0,
                satiety = 100,
                status = 'alive',
                alert_sent = 0
            WHERE user_id = ?
        ''', (user_id,))
        await db.commit()

    is_user_admin = await is_admin(user_id)
    is_fake = await is_fake_admin(user_id)
    await message.answer(
        "🧪 Dev Test активирован!\n\n"
        "🦔 Вы получили обычного ежа — бесплатно!\n"
        "🍖 Сытость: 100%\n\n"
        "Теперь вы снова в игре!",
        reply_markup=main_reply_keyboard(is_user_admin, is_fake)
    )
    await message.answer("Меню:", reply_markup=main_menu_keyboard(is_user_admin))

# =====================================
# 📱 REPLY КНОПКИ (внизу экрана)
# =====================================

@router.message(F.text == "🏠 Меню")
async def reply_menu(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_banned, ban_reason = await check_user_banned(user_id)
    if is_banned:
        await message.answer(f"🚫 Вы заблокированы!\n\nПричина: {ban_reason or 'Не указана'}")
        return
    try:
        await update_username(user_id, message.from_user.username or "Unknown")
    except Exception:
        pass
    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    if user['status'] != 'alive':
        await message.answer("🪦 Вы в посмертии...", reply_markup=death_reply_keyboard())
        return
    is_user_admin = await is_admin(user_id)
    is_fake = await is_fake_admin(user_id)
    try:
        text = f"Привет! 👋🦔\nТвой номер игрока: {format_player_number(user['player_number'])}"
        await message.answer(text, reply_markup=main_reply_keyboard(is_user_admin, is_fake))
        await message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
    except Exception:
        try:
            await message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
        except:
            pass


@router.message(F.text == "🦔 Мой Ёж")
async def reply_my_hedgehog(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    join_date = datetime.strptime(user['join_date'], "%Y-%m-%d %H:%M:%S")
    days_in_bot = (datetime.now() - join_date).days
    injured_text = "\n\n🩹 Твоя рука поранена! Купи аптечку в магазине!" if user['is_injured'] else ""
    
    cls_name = CLASSES.get(user['hedgehog_class'], {'name': 'Unknown'})['name']
    
    await message.answer(
        f"🦔 Это ваш ежик! 🦔\n"
        f"Класс: {cls_name}\n"
        f"🎫 Номер игрока: {format_player_number(user['player_number'])}\n"
        f"🧸 Имя ежа: {user['hedgehog_name']}\n"
        f"🎨 Цвет иголок: {user['hedgehog_color']}\n"
        f"🍖 Сытость: {int(user['satiety'])}%\n"
        f"🕘 Дней в боте с ежиком 🦔 - {days_in_bot}\n"
        f"🐘 Кожа слона: {user['elephant_skin']}\n"
        f"💎 Алмазы: {user['diamonds']}\n"
        f"👬 Приглашено друзей: {user['referrals_count']}\n"
        f"👬🎁 Заработано с друзей: {user['referrals_earned']} Ежидзиков👍{injured_text}",
        reply_markup=my_hedgehog_keyboard(user['hedgehog_class'])
    )


@router.message(F.text == "🌟 Финансы")
async def reply_finances(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы! Нажмите /start")
        return
    is_user_admin = await is_admin(message.from_user.id)
    status = "👑 Админ" if is_user_admin else "🎮 Игрок"
    
    await message.answer(
        f"🦔🌟 В этом разделе все по твоим деньгам 🌟🦔\n\n"
        f"Твой баланс: {user['balance']} Ежидзиков👍\n"
        f"🐘 Кожа слона: {user['elephant_skin']}\n"
        f"💎 Алмазы: {user['diamonds']}\n"
        f"Твой статус: {status}",
        reply_markup=finances_keyboard()
    )


@router.message(F.text == "🤔 Поддержка")
async def reply_support(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    is_main = await is_main_admin(message.from_user.id)
    await message.answer("🦔🦔🦔", reply_markup=support_keyboard(is_main))


@router.message(F.text == "🎰 Ежино")
async def reply_casino(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    media_info = await get_screen_media("casino")
    text = (
        "🎰 Это — ЕЖИНО! 🔔\n"
        "В этом месте ты можешь сильно разбогатеть! 🏆 (или опустить баланс, возможно даже не на немного)\n\n"
        "🦔 Выбери игру, в которую будешь играть! 🎰"
    )
    
    if media_info:
        try:
            if media_info['media_type'] == 'photo':
                await message.answer_photo(media_info['file_id'], caption=text, reply_markup=casino_keyboard())
            else:
                await message.answer_video(media_info['file_id'], caption=text, reply_markup=casino_keyboard())
        except:
            await message.answer(text, reply_markup=casino_keyboard())
    else:
        await message.answer(text, reply_markup=casino_keyboard())


@router.message(F.text == "🛠 Панель")
async def reply_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    if await is_admin(user_id):
        # Реальный админ -> AdminOS
        await message.answer(
            "🔒 **Hedgehog AdminOS v3.8**\nДоступ разрешен. Загрузка модулей...",
            reply_markup=admin_os_login_keyboard(),
            parse_mode="Markdown"
        )
    elif await is_fake_admin(user_id):
        # Фейк админ -> Троллинг
        await message.answer(
            "🔒 **Hedgehog AdminOS**\nОбнаружена попытка входа. Требуется авторизация...",
            reply_markup=fake_admin_keyboard(),
            parse_mode="Markdown"
        )
    else:
        # Обычный игрок (не должен видеть кнопку, но на всякий случай)
        pass

@router.callback_query(F.data == "admin_login_verify")
async def admin_login_verify(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Ошибка доступа!", show_alert=True)
        return
    
    await safe_edit_text(
        callback.message,
        "💻 **Hedgehog AdminOS**\nВыберите категорию:",
        reply_markup=admin_main_keyboard(),
        parse_mode="Markdown"
    )


# =====================================
# 🧪 IMAGE TEST
# =====================================

@router.message(F.text == "Image Test")
async def image_test_start(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(bot, message.from_user.id, message=message):
        return
    if not HAS_PILLOW:
        await message.answer("⚠️ Функция недоступна (нет библиотеки Pillow).")
        return
        
    await state.set_state(UserStates.image_test_text)
    await message.answer(
        "🧪 Image Test\n\nВведите текст, который нужно нарисовать на картинке:",
        reply_markup=image_test_keyboard()
    )

@router.message(UserStates.image_test_text)
async def image_test_generate(message: Message, state: FSMContext):
    if not HAS_PILLOW:
        return
    
    text = message.text
    if not text:
        await message.answer("Отправь текст!")
        return
    
    try:
        width, height = 512, 512
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
            
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
             text_width, text_height = draw.textsize(text, font=font)

        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        draw.text((x, y), text, fill="black", font=font)
        
        bio = io.BytesIO()
        image.save(bio, 'JPEG')
        bio.seek(0)
        
        input_file = BufferedInputFile(bio.read(), filename="image_test.jpg")
        
        await message.answer_photo(input_file, caption=f"✅ Вот твой текст:\n{text}")
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации: {e}")
        await state.clear()

@router.callback_query(F.data == "cancel_image_test")
async def cancel_image_test(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_delete(callback.message)
    await callback.message.answer("Отменено.")

# =====================================
# 🥕 ПОКОРМИТЬ (v3.8 Diamond Drop)
# =====================================

@router.callback_query(F.data == "feed")
async def feed_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    await safe_edit_text(
        callback.message,
        f"Покорми своего ежика тут 👇\n"
        f"Текущая сытость: {int(user['satiety'])}%\n"
        "Если долго не кормить ежа, он умрёт! ☠️",
        reply_markup=feed_keyboard(),
        media_screen="feed"
    )

@router.callback_query(F.data.startswith("feed_item_"))
async def do_feed_item(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    idx = int(callback.data.replace("feed_item_", ""))
    if idx < 0 or idx >= len(FOOD_ITEMS):
        await callback.answer("❌ Товар не найден!", show_alert=True)
        return
    name, price, sat_add = FOOD_ITEMS[idx]
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    balance = user['balance']
    current_sat = user['satiety']
    
    cls_data = CLASSES.get(user['hedgehog_class'])
    max_sat = cls_data['max_satiety'] if cls_data else 100
    
    if balance < price:
        await callback.answer(f"❌ Нужно {price} Ежидзиков!", show_alert=True)
        return
    
    if current_sat >= max_sat:
        await callback.answer("🤢 Ёжик не голоден!", show_alert=True)
        return
    
    new_sat = min(current_sat + sat_add, max_sat)
    
    # Diamond Drop Logic (1%)
    diamond_dropped = False
    diamond_msg = ""
    if random.random() < 0.01:
        diamond_dropped = True
        diamond_msg = "\n\n💎 КХЕ-КХЕ... Ёж подавился и выплюнул АЛМАЗ! 💎"
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance = balance - ?, total_feedings = total_feedings + 1, satiety = ?, alert_sent = 0 WHERE user_id = ?",
            (price, new_sat, user_id)
        )
        if diamond_dropped:
            await db.execute("UPDATE users SET diamonds = diamonds + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
    
    await add_stat(user_id, "feeding", 1)
    
    if diamond_dropped:
         actual_gain = int(new_sat - current_sat)
         await callback.message.answer(f"😋 Ам-ням! +{actual_gain}% сытости{diamond_msg}")
    else:
         actual_gain = int(new_sat - current_sat)
         await callback.answer(f"😋 Ам-ням! +{actual_gain}% сытости")
    
    # Refresh menu
    user = await get_user(user_id)
    await safe_edit_text(
        callback.message,
        f"Покорми своего ежика тут 👇\n"
        f"Текущая сытость: {int(user['satiety'])}%\n"
        "Если долго не кормить ежа, он умрёт! ☠️",
        reply_markup=feed_keyboard(),
        media_screen="feed"
    )

# =====================================
# 🤚 ПОГЛАДИТЬ (v3.8 Diamond Drop)
# =====================================

@router.callback_query(F.data == "pet")
async def pet_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    if user['is_injured']:
        await safe_edit_text(
            callback.message,
            "🦔🙀 Пока ты гладил ежа, ты случайно укололся!\n\n"
            "😞 Теперь ты не можешь гладить ежа, пока не вылечишь свою руку!\n"
            "Вылечить руку поможет аптечка! 🩹\n"
            "Аптечка доступна в магазине! 🧳",
            reply_markup=injured_keyboard()
        )
        return
    
    happiness = user['happiness']
    
    await safe_edit_text(
        callback.message,
        f"😁 Погладь своего ежа 🦔 😁\n"
        f"Если ты достаточно погладишь ежа, он откуда то возьмёт деньги\n\n"
        f"Уровень радости 💫 - {happiness:.1f}%\n"
        f"Каждый раз когда ты гладишь ежа, уровень радости повышается! 💯",
        reply_markup=pet_keyboard(),
        media_screen="pet"
    )


@router.callback_query(F.data == "do_pet")
async def do_pet(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    if user['is_injured']:
        await callback.answer("🩹 Сначала вылечи руку!", show_alert=True)
        return
    
    # Diamond Drop Logic (1%)
    if random.random() < 0.01:
        async with aiosqlite.connect(DB_NAME) as db:
             await db.execute("UPDATE users SET diamonds = diamonds + 1 WHERE user_id = ?", (user_id,))
             await db.commit()
        await callback.message.answer("💎 ВАУ! Пока ты гладил ежа, у него из иголок выпал АЛМАЗ! 💎")

    # Расчет шанса укола (Ejidze +5%)
    base_injure = 0.1
    if user['hedgehog_class'] == 'ejidze':
        base_injure += 0.05
        
    if random.random() < base_injure:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET is_injured = 1 WHERE user_id = ?", (user_id,))
            await db.commit()
        
        await safe_edit_text(
            callback.message,
            "🦔🙀 Пока ты гладил ежа, ты случайно укололся!\n\n"
            "😞 Теперь ты не можешь гладить ежа, пока не вылечишь свою руку!\n"
            "Вылечить руку поможет аптечка! 🩹\n"
            "Аптечка доступна в магазине! 🧳",
            reply_markup=injured_keyboard()
        )
        return
    
    happiness = user['happiness']
    add_happiness = round(random.uniform(0.1, 2.0), 1)
    happiness += add_happiness
    
    if happiness >= 100:
        base_reward = random.randint(50, 100)
        # Golden bonus
        if user['hedgehog_class'] == 'golden':
            base_reward += 50
            
        await update_balance(user_id, base_reward)
        
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET happiness = 0 WHERE user_id = ?", (user_id,))
            await db.commit()
        
        await callback.message.answer(
            f"🎉 УРОВЕНЬ РАДОСТИ ДОСТИГ 100%! 🎉\n"
            f"Еж нашёл для тебя {base_reward} Ежидзиков👍!",
            reply_markup=back_button("menu")
        )
        happiness = 0
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET happiness = ? WHERE user_id = ?", (happiness, user_id))
            await db.commit()
    
    await safe_edit_text(
        callback.message,
        f"😁 Погладь своего ежа 🦔 😁\n"
        f"Уровень радости 💫 - {happiness:.1f}% (+{add_happiness}%)\n",
        reply_markup=pet_keyboard()
    )
    
    await callback.answer(f"+{add_happiness}% радости!")


# =====================================
# 🦔 МОЙ ЕЖ (Кастомизация + Store/Sell)
# =====================================

@router.callback_query(F.data == "my_hedgehog")
async def callback_my_hedgehog(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    join_date = datetime.strptime(user['join_date'], "%Y-%m-%d %H:%M:%S")
    days_in_bot = (datetime.now() - join_date).days
    injured_text = "\n\n🩹 Твоя рука поранена! Купи аптечку в магазине!" if user['is_injured'] else ""
    cls_name = CLASSES.get(user['hedgehog_class'], {'name': 'Unknown'})['name']
    await safe_edit_text(
        callback.message,
        f"🦔 Это ваш ежик! 🦔\n"
        f"Класс: {cls_name}\n"
        f"🎫 Номер игрока: {format_player_number(user['player_number'])}\n"
        f"🧸 Имя ежа: {user['hedgehog_name']}\n"
        f"🎨 Цвет иголок: {user['hedgehog_color']}\n"
        f"🍖 Сытость: {int(user['satiety'])}%\n"
        f"🕘 Дней в боте с ежиком 🦔 - {days_in_bot}\n"
        f"🐘 Кожа слона: {user['elephant_skin']}\n"
        f"💎 Алмазы: {user['diamonds']}\n"
        f"👬 Приглашено друзей: {user['referrals_count']}\n"
        f"👬🎁 Заработано с друзей: {user['referrals_earned']} Ежидзиков👍{injured_text}",
        reply_markup=my_hedgehog_keyboard(user['hedgehog_class'])
    )


@router.callback_query(F.data == "customize")
async def customize(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(
        callback.message,
        "🖌️ Кастомизация ежа 🦔\n\n"
        "Выбери что хочешь изменить:",
        reply_markup=customize_keyboard()
    )


@router.callback_query(F.data == "change_name")
async def change_name(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await state.set_state(UserStates.waiting_name)
    await safe_edit_text(
        callback.message,
        "✏️ Введи новое имя для ежа:",
        reply_markup=back_button("customize")
    )


@router.message(UserStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    new_name = message.text[:50]
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET hedgehog_name = ? WHERE user_id = ?", (new_name, user_id))
        await db.commit()
    
    await state.clear()
    is_user_admin = await is_admin(user_id)
    await message.answer(
        f"✅ Имя ежа изменено на: {new_name}",
        reply_markup=main_menu_keyboard(is_user_admin)
    )


@router.callback_query(F.data == "change_color")
async def change_color(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    balance = await get_balance(callback.from_user.id)
    await safe_edit_text(
        callback.message,
        f"🎨 Выбери цвет иголок (100 Ежидзиков👍)\n"
        f"💰 Твой баланс: {balance} Ежидзиков👍",
        reply_markup=colors_keyboard()
    )


@router.callback_query(F.data.startswith("color_"), ~StateFilter(AdminStates.waiting_promo_value))
async def select_color(callback: CallbackQuery, state: FSMContext):
    
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    color_id = callback.data.replace("color_", "")
    color_name = COLORS.get(color_id, "Не выбран")
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET balance = balance - 100, hedgehog_color = ? WHERE user_id = ? AND balance >= 100",
            (color_name, user_id)
        )
        if cursor.rowcount == 0:
            await callback.answer("❌ Недостаточно Ежидзиков! Нужно 100.", show_alert=True)
            return
        await db.commit()
    
    await callback.answer(f"✅ Цвет изменён на {color_name}!")
    
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    await callback.message.edit_text(
        f"✅ Цвет иголок изменён на: {color_name}\n"
        f"💰 Списано 100 Ежидзиков👍",
        reply_markup=my_hedgehog_keyboard(user['hedgehog_class'])
    )

@router.callback_query(F.data == "store_hedgehog")
async def store_hedgehog(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET status = 'stored' WHERE user_id = ?", (user_id,))
        await db.commit()
    
    await callback.answer("🤝 Ёж отдан на хранение!")
    await callback.message.answer(
        "🤝 Вы отдали ежа на хранение!\n"
        "Теперь он живет в роскоши, а вы...",
        reply_markup=death_reply_keyboard()
    )

@router.callback_query(F.data == "sell_hedgehog")
async def sell_hedgehog(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    cls_data = CLASSES.get(user['hedgehog_class'])
    if not cls_data: return

    refund = int(cls_data['price'] * 0.75)
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET status = 'sold', balance = balance + ? WHERE user_id = ?", (refund, user_id))
        await db.commit()

    await callback.answer("💸 Ёж продан!")
    await callback.message.answer(
        f"💸 Вы продали ежа!\n"
        f"Получено: {refund} Ежидзиков👍 (75% от стоимости)",
        reply_markup=death_reply_keyboard()
    )

# =====================================
# 🌟 ФИНАНСЫ И ТОПЫ
# =====================================

@router.callback_query(F.data == "finances")
async def finances_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    is_user_admin = await is_admin(callback.from_user.id)
    status = "👑 Админ" if is_user_admin else "🎮 Игрок"
    
    await safe_edit_text(
        callback.message,
        f"🦔🌟 В этом разделе все по твоим деньгам 🌟🦔\n\n"
        f"Твой баланс: {user['balance']} Ежидзиков👍\n"
        f"🐘 Кожа слона: {user['elephant_skin']}\n"
        f"💎 Алмазы: {user['diamonds']}\n"
        f"Твой статус: {status}",
        reply_markup=finances_keyboard()
    )

@router.callback_query(F.data == "top_balance")
async def top_balance_menu(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(
        callback.message,
        "🏆 Топ по ежидзикам👍\n\nВыбери период:",
        reply_markup=top_period_keyboard("topbal")
    )

@router.callback_query(F.data == "top_skin")
async def top_skin_show(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    users = await get_top_users("elephant_skin")
    await safe_edit_text(
        callback.message,
        format_top(users, "🏆 Топ по коже слона🐘", value_key="value"),
        reply_markup=back_button("finances")
    )

@router.callback_query(F.data == "top_feedings_period")
async def top_feedings_menu(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(
        callback.message,
        "🏆 Топ по кормлениям+\n\nВыбери период:",
        reply_markup=top_period_keyboard("topfeed")
    )


async def get_top_users(order_by: str, limit: int = 10):
    ALLOWED_ORDER = {"balance", "elephant_skin", "total_feedings", "referrals_count", "diamonds"}
    if order_by not in ALLOWED_ORDER:
        raise ValueError(f"Invalid order_by: {order_by}")
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(f'''
            SELECT hedgehog_name, hedgehog_color, player_number, hedgehog_class, {order_by} as value 
            FROM users ORDER BY {order_by} DESC LIMIT ?
        ''', (limit,)) as cursor:
            return await cursor.fetchall()


async def get_top_by_stats(action_type: str, period: str, limit: int = 10):
    now = datetime.now()
    
    if period == "hour":
        since = now - timedelta(hours=1)
    elif period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(weeks=1)
    elif period == "month":
        since = now - timedelta(days=30)
    else:
        since = datetime(2000, 1, 1)
    
    since_str = since.strftime("%Y-%m-%d %H:%M:%S")
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT u.hedgehog_name, u.hedgehog_color, u.player_number, u.hedgehog_class, COALESCE(SUM(s.amount), 0) as value
            FROM users u
            LEFT JOIN stats s ON s.user_id = u.user_id AND s.action_type = ? AND s.timestamp >= ?
            GROUP BY u.user_id
            HAVING value > 0
            ORDER BY value DESC
            LIMIT ?
        ''', (action_type, since_str, limit)) as cursor:
            return await cursor.fetchall()


def format_top(users, title: str, value_key: str = "value") -> str:
    if not users:
        return f"{title}\n\n😔 Пока никого нет..."
    
    text = f"{title}\n\n"
    for i, user in enumerate(users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        player_num = format_player_number(user['player_number']) if user['player_number'] else ""
        # Class icon
        cls_icon = "🤠" if user['hedgehog_class'] == "ejidze" else "🦔"
        text += f"{medal} {cls_icon}{user['hedgehog_name']} {player_num} - {int(user[value_key])}\n"
    return text


@router.callback_query(F.data.startswith("topbal_"))
async def show_top_balance(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    period = callback.data.replace("topbal_", "")
    
    if period == "all":
        users = await get_top_users("balance")
        title = "🏆 Топ по ежидзикам👍 (за всё время)"
    else:
        users = await get_top_by_stats("balance_add", period)
        period_names = {"hour": "за час", "day": "за день", "week": "за неделю", "month": "за месяц"}
        title = f"🏆 Топ по ежидзикам👍 ({period_names.get(period, period)})"
    
    await safe_edit_text(
        callback.message,
        format_top(users, title),
        reply_markup=back_button("finances")
    )


@router.callback_query(F.data.startswith("topfeed_"))
async def show_top_feedings(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    period = callback.data.replace("topfeed_", "")
    
    if period == "all":
        users = await get_top_users("total_feedings")
        title = "🏆 Топ по кормлениям (за всё время)"
    else:
        users = await get_top_by_stats("feeding", period)
        period_names = {"hour": "за час", "day": "за день", "week": "за неделю", "month": "за месяц"}
        title = f"🏆 Топ по кормлениям+ ({period_names.get(period, period)})"
    
    await safe_edit_text(
        callback.message,
        format_top(users, title),
        reply_markup=back_button("finances")
    )


@router.callback_query(F.data == "top_feedings_all")
async def show_top_feedings_all(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    users = await get_top_users("total_feedings")
    await safe_edit_text(
        callback.message,
        format_top(users, "🏆 Топ по кормлениям (за всё время)"),
        reply_markup=back_button("finances")
    )


@router.callback_query(F.data == "top_referrals")
async def show_top_referrals(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    users = await get_top_users("referrals_count")
    await safe_edit_text(
        callback.message,
        format_top(users, "🏆 Топ по рефералам"),
        reply_markup=back_button("finances")
    )


# =====================================
# 🐜 МУРАВЬИ
# =====================================

@router.callback_query(F.data == "ants")
async def ants_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    ant_chance = user['ant_chance']
    
    # Bonus for Ejidze
    if user['hedgehog_class'] == 'ejidze':
        ant_chance += 10.0

    ant_cost = await get_setting("ant_catch_cost", "200")
    
    await safe_edit_text(
        callback.message,
        f"🐜 Пусть твой ёж попробует забрать муравьев с поля! 🐜\n\n"
        f"Цена🌟 - {ant_cost} ежидзиков!\n"
        f"С шансом {ant_chance:.1f}% еж сможет поймать муравья и тогда он будет тебе приносить доход!!! 🕘",
        reply_markup=ants_keyboard()
    )


@router.callback_query(F.data == "catch_ant")
async def catch_ant(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    balance = user['balance']
    ant_chance = user['ant_chance']
    if user['hedgehog_class'] == 'ejidze': ant_chance += 10.0
    
    ant_cost = int(await get_setting("ant_catch_cost", "200"))
    ant_income = int(await get_setting("ant_income", "10"))

    if balance < ant_cost:
        await callback.answer(f"❌ Недостаточно Ежидзиков! Нужно {ant_cost}.", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (ant_cost, user_id))
        await db.commit()
    
    if random.random() * 100 < ant_chance:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET ants = ants + 1 WHERE user_id = ?", (user_id,))
            await db.commit()
        
        await callback.answer("🎉 УРА! Ты поймал муравья! 🐜", show_alert=True)
        await safe_edit_text(
            callback.message,
            f"🎉 ПОЙМАЛ МУРАВЬЯ! 🐜\n\n"
            f"Теперь он будет приносить тебе {ant_income} Ежидзиков👍 в час!",
            reply_markup=back_button("ants")
        )
    else:
        await callback.answer("😔 Муравей убежал...", show_alert=True)
        user = await get_user(user_id)
        await safe_edit_text(
            callback.message,
            f"😔 Муравей убежал...\n\n"
            f"Попробуй ещё раз!\n"
            f"💰 Баланс: {user['balance']} Ежидзиков👍",
            reply_markup=ants_keyboard()
        )


@router.callback_query(F.data == "manage_ants")
async def manage_ants(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    ants = user['ants']
    ant_income = int(await get_setting("ant_income", "10"))
    income = ants * ant_income
    
    await safe_edit_text(
        callback.message,
        f"⚙️ Управление муравьями 🐜\n\n"
        f"🐜 У тебя муравьёв: {ants}\n"
        f"💰 Доход: {income} Ежидзиков👍/час",
        reply_markup=manage_ants_keyboard()
    )


@router.callback_query(F.data == "delete_ant")
async def delete_ant(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if user['ants'] <= 0:
        await callback.answer("❌ У тебя нет муравьёв!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ants = ants - 1 WHERE user_id = ?", (user_id,))
        await db.commit()
    
    await callback.answer("🗑️ Муравей удалён!", show_alert=True)
    
    await manage_ants(callback)


# =====================================
# 👬 ПРИГЛАСИТЬ ДРУГА
# =====================================

@router.callback_query(F.data == "invite")
async def invite(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    full_text = (
        f"🎁👬 Приглашай друзей и получай крутые бонусы! И друзья тоже их получат! 🎁\n\n"
        f"🎁 Бонус для тебя:\n"
        f"- ПРОМОКОД НА 10 ЕЖИДЗИКОВ👍! 🎁\n"
        f"- 20 ежидзиков👍\n"
        f"- увеличение шанса поймать муравья (+0.3%, максимально 30%)\n"
        f"- на 20 минут увеличенный доход с рекламы в 2 раза!\n"
        f"- повышение в топе (возможно)\n\n"
        f"🎁 Бонус для друга:\n"
        f"- 200 ежидзиков на старте, вместо 0! 🔔\n\n"
        f"Твоя ссылка (отправь другу/подруге):\n"
        f"{invite_link}"
    )

    # Стриминг через sendMessageDraft
    draft_id = random.randint(1, 2**31 - 1)
    chat_id = callback.message.chat.id

    try:
        # Показываем "Думает..."
        await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text="")
        await asyncio.sleep(0.3)

        # Постепенно добавляем текст
        current = ""
        chunk_size = 8
        for i in range(0, len(full_text), chunk_size):
            current += full_text[i:i + chunk_size]
            await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text=current)
            await asyncio.sleep(0.03)

        # Финальное сообщение (draft исчезает через ~30 сек, поэтому сохраняем)
        await callback.message.answer(full_text, reply_markup=back_button("menu"))
    except Exception:
        # Fallback если стриминг не поддерживается
        await safe_edit_text(
            callback.message,
            full_text,
            reply_markup=back_button("menu")
        )


# =====================================
# 📞 ПОЗВОНИТЬ ЕЖУ
# =====================================

@router.callback_query(F.data == "call")
async def call_hedgehog(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(callback.message, "📞 Звонок ежу 📞\n\n🔄 Соединение...", media_screen="call")
    
    await asyncio.sleep(random.randint(5, 10))
    
    answer = random.choice(["ДА!", "НЕТ!"])
    
    await safe_edit_text(
        callback.message,
        f"📞 Еж ответил!\n"
        f"📞 Еж сказал: {answer}",
        reply_markup=back_button("menu")
    )

# =====================================
# ♻️ ОБМЕННИК
# =====================================

@router.callback_query(F.data == "exchange")
async def exchange_menu(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    text = (
        f"🦔♻️ Здесь можно обменять валюту!\n\n"
        f"⚡ Курс покупки: 45 Ежидзиков👍 = 1 Кожа слона\n"
        f"⚡ Курс продажи: 1 Кожа слона = 45 Ежидзиков👍\n\n"
        f"У тебя:\n"
        f"💰 {user['balance']} Ежидзиков👍\n"
        f"🐘 {user['elephant_skin']} Кожи слона"
    )

    await safe_edit_text(callback.message, text, reply_markup=exchange_keyboard(), media_screen="exchange")

@router.callback_query(F.data == "do_exchange_to_skin")
async def process_exchange_to_skin(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
        
    cost = 45
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET balance = balance - ?, elephant_skin = elephant_skin + 1 WHERE user_id = ? AND balance >= ?", (cost, user_id, cost))
        if cursor.rowcount == 0:
            await callback.answer(f"❌ Нужно {cost} Ежидзиков!", show_alert=True)
            return
        await db.commit()
    
    await callback.answer("✅ Обмен выполнен! +1 Кожа слона")
    await exchange_menu(callback)

@router.callback_query(F.data == "do_exchange_to_balance")
async def process_exchange_to_balance(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
        
    user_id = callback.from_user.id
    reward = 45

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET elephant_skin = elephant_skin - 1, balance = balance + ? WHERE user_id = ? AND elephant_skin >= 1", (reward, user_id))
        if cursor.rowcount == 0:
            await callback.answer("❌ У тебя нет Кожи слона!", show_alert=True)
            return
        await db.commit()
    
    await callback.answer(f"✅ Обмен выполнен! +{reward} Ежидзиков👍")
    await exchange_menu(callback)

# =====================================
# 💎 АЛМАЗЫ (v3.8)
# =====================================

@router.callback_query(F.data == "diamond_menu")
async def diamond_menu(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback): return
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    await safe_edit_text(
        callback.message,
        f"💎 МЕНЮ АЛМАЗОВ 💎\n\n"
        f"Алмазы - это супер-редкая валюта!\n"
        f"Их можно найти случайно при кормлении или купить за Кожу Слона.\n\n"
        f"Твой баланс: {user['diamonds']} 💎\n"
        f"🐘 Кожи слона: {user['elephant_skin']}",
        reply_markup=diamond_menu_keyboard()
    )

@router.callback_query(F.data == "ex_skin_to_dia")
async def ex_skin_to_dia(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    if user['elephant_skin'] < 3:
        await callback.answer("❌ Нужно 3 Кожи слона!", show_alert=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET elephant_skin = elephant_skin - 3, diamonds = diamonds + 1 WHERE user_id = ? AND elephant_skin >= 3", (user['user_id'],))
        if cursor.rowcount == 0:
            await callback.answer("❌ Нужно 3 Кожи слона!", show_alert=True)
            return
        await db.commit()
    await callback.answer("✅ +1 Алмаз!")
    await diamond_menu(callback)

@router.callback_query(F.data == "ex_dia_to_skin")
async def ex_dia_to_skin(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    if user['diamonds'] < 1:
        await callback.answer("❌ У тебя нет алмазов!", show_alert=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET diamonds = diamonds - 1, elephant_skin = elephant_skin + 3 WHERE user_id = ? AND diamonds >= 1", (user['user_id'],))
        if cursor.rowcount == 0:
            await callback.answer("❌ У тебя нет алмазов!", show_alert=True)
            return
        await db.commit()
    await callback.answer("✅ +3 Кожи слона!")
    await diamond_menu(callback)

@router.callback_query(F.data == "top_diamonds")
async def top_diamonds(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    users = await get_top_users("diamonds")
    await safe_edit_text(
        callback.message,
        format_top(users, "🏆 Топ богачей (Алмазы)", value_key="value"),
        reply_markup=back_button("diamond_menu")
    )


# =====================================
# 💸 ПЕРЕВОД
# =====================================

@router.callback_query(F.data == "transfer_menu")
async def transfer_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(
        callback.message,
        "💸 Перевод Ежидзиков👍 другому игроку\n\n"
        "⚠️ Комиссия 5%\n"
        "Минимальная сумма: 10",
        reply_markup=transfer_keyboard(),
        media_screen="transfer"
    )

@router.callback_query(F.data == "start_transfer")
async def start_transfer(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await state.set_state(UserStates.transfer_user)
    await safe_edit_text(
        callback.message,
        "👤 Введите ID, @username или #номер игрока, которому хотите перевести деньги:",
        reply_markup=back_button("transfer_menu")
    )

@router.message(UserStates.transfer_user)
async def process_transfer_user(message: Message, state: FSMContext):
    user = await find_user_flexible(message.text.strip())
    
    if not user:
        await message.answer("❌ Игрок не найден! Попробуйте снова.")
        return
    
    if user['user_id'] == message.from_user.id:
        await message.answer("❌ Нельзя переводить самому себе!")
        return

    await state.update_data(recipient_id=user['user_id'], recipient_name=user['username'])
    await state.set_state(UserStates.transfer_amount)
    
    await message.answer(
        f"💸 Получатель: @{user['username']} ({format_player_number(user['player_number'])})\n"
        f"💰 Ваш баланс: {await get_balance(message.from_user.id)}\n\n"
        "Введите сумму перевода:",
        reply_markup=back_button("transfer_menu")
    )

@router.message(UserStates.transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 10:
            raise ValueError
    except:
        await message.answer("❌ Введите целое число больше 10!")
        return
        
    sender_id = message.from_user.id
    
    data = await state.get_data()
    recipient_id = data['recipient_id']
    
    commission = int(amount * 0.05)
    to_receive = amount - commission
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (amount, sender_id, amount))
        if cursor.rowcount == 0:
            await message.answer("❌ Недостаточно средств!")
            return
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (to_receive, recipient_id))
        await db.commit()
    
    try:
        await bot.send_message(recipient_id, f"💸 Вам пришел перевод!\n+{to_receive} Ежидзиков👍 от @{message.from_user.username}")
    except:
        pass
        
    await state.clear()
    await message.answer(
        f"✅ Перевод успешно выполнен!\n\n"
        f"📤 Списано: {amount}\n"
        f"📉 Комиссия: {commission}\n"
        f"📥 Зачислено: {to_receive}",
        reply_markup=main_menu_keyboard(await is_admin(sender_id))
    )

# =====================================
# 🌐 САЙТ
# =====================================

@router.callback_query(F.data == "website")
async def website_info(callback: CallbackQuery):
    text = (
        "🌐 Это официальный сайт 🦔\n\n"
        "Там будут новости, обновления и приколы."
    )
    await safe_edit_text(callback.message, text, reply_markup=back_button("menu"), media_screen="website")

# =====================================
# 🚧 STUBS (Заглушки)
# =====================================
@router.callback_query(F.data.in_(["stub_forge", "stub_ai"]))
async def stub_handler(callback: CallbackQuery):
    await callback.answer("🚧 Раздел в разработке!\nСледите за новостями.", show_alert=True)

# =====================================
# 🎰 КАЗИНО (ЕЖИНО)
# =====================================

@router.callback_query(F.data == "casino")
async def casino_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    media_info = await get_screen_media("casino")
    text = (
        "🎰 Это — ЕЖИНО! 🔔\n"
        "В этом месте ты можешь сильно разбогатеть! 🏆 (или опустить баланс, возможно даже не на немного)\n\n"
        "🦔 Выбери игру, в которую будешь играть! 🎰"
    )
    
    await safe_edit_text(callback.message, text, reply_markup=casino_keyboard(), media_screen="casino")


# 🎲 БРОСИТЬ КУБИК
@router.callback_query(F.data == "casino_dice")
async def casino_dice(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    
    await safe_edit_text(
        callback.message,
        f"🎲 Бросить кубик\n\n"
        f"Выбери 3 числа от 1 до 6.\n"
        f"Если кубик покажет одно из твоих чисел — ×2 от ставки!\n"
        f"Если нет — теряешь ставку.\n\n"
        f"💰 Твой баланс: {user['balance']} Ежидзиков👍\n\n"
        f"Выбери ставку:",
        reply_markup=casino_bet_keyboard("dice")
    )


@router.callback_query(F.data.startswith("bet_dice_"), F.data != "bet_dice_custom")
async def bet_dice(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    bet = int(callback.data.replace("bet_dice_", ""))
    balance = await get_balance(callback.from_user.id)
    
    if balance < bet:
        await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
        return
    
    await state.update_data(bet=bet, selected_numbers=[])
    await state.set_state(UserStates.dice_numbers)
    
    await safe_edit_text(
        callback.message,
        f"🎲 Ставка: {bet} Ежидзиков👍\n\n"
        f"Выбери 3 числа (1-6):",
        reply_markup=dice_numbers_keyboard([])
    )


@router.callback_query(F.data.startswith("dice_num_"), UserStates.dice_numbers)
async def dice_select_number(callback: CallbackQuery, state: FSMContext):
    num = int(callback.data.replace("dice_num_", ""))
    data = await state.get_data()
    selected = data.get('selected_numbers', [])
    
    if num in selected:
        selected.remove(num)
    elif len(selected) < 3:
        selected.append(num)
    else:
        await callback.answer("Уже выбрано 3 числа! Нажми на число чтобы убрать.", show_alert=True)
        return
    
    await state.update_data(selected_numbers=selected)
    await safe_edit_text(
        callback.message,
        f"🎲 Ставка: {data['bet']} Ежидзиков👍\n\n"
        f"Выбери 3 числа (1-6):\n"
        f"Выбрано: {selected if selected else 'ничего'}",
        reply_markup=dice_numbers_keyboard(selected)
    )


@router.callback_query(F.data == "dice_roll", UserStates.dice_numbers)
async def dice_roll(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data['bet']
    selected = data['selected_numbers']
    user_id = callback.from_user.id
    
    balance = await get_balance(user_id)
    if balance < bet:
        await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
        await state.clear()
        return
    
    await state.clear()
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (bet, user_id, bet))
        if cursor.rowcount == 0:
            await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
            return
        await db.commit()
    
    result = random.randint(1, 6)
    
    if result in selected:
        win = bet * 2
        await update_balance(user_id, win)
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE users SET casino_wins = casino_wins + 1, total_casino_profit = total_casino_profit + ? WHERE user_id = ?",
                (win - bet, user_id)
            )
            await db.commit()
        
        await safe_edit_text(
            callback.message,
            f"🎲 Кубик показал: {result}\n\n"
            f"🎉 ПОБЕДА! Твои числа: {selected}\n"
            f"💰 +{win} Ежидзиков👍!",
            reply_markup=back_button("casino")
        )
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE users SET casino_losses = casino_losses + 1, total_casino_profit = total_casino_profit - ? WHERE user_id = ?",
                (bet, user_id)
            )
            await db.commit()
        
        await safe_edit_text(
            callback.message,
            f"🎲 Кубик показал: {result}\n\n"
            f"😔 Мимо... Твои числа были: {selected}\n"
            f"💸 -{bet} Ежидзиков👍",
            reply_markup=back_button("casino")
        )

# Обработка Своей ставки (Общая для всех игр)
@router.callback_query(F.data.endswith("_custom"))
async def custom_bet_input(callback: CallbackQuery, state: FSMContext):
    game_type = callback.data.split("_")[1] # bet_dice_custom -> dice
    await state.set_state(UserStates.custom_bet_amount)
    await state.update_data(game_type=game_type)
    await safe_edit_text(
        callback.message,
        "🖊 Введите сумму ставки (числом):",
        reply_markup=back_button("casino")
    )

@router.message(UserStates.custom_bet_amount)
async def process_custom_bet(message: Message, state: FSMContext):
    try:
        bet = int(message.text)
        if bet <= 0: raise ValueError
        if bet > 2000000000: # Max bet check
            await message.answer("❌ Слишком большая ставка! Макс: 2 млрд")
            return
    except:
        await message.answer("❌ Введите положительное число!")
        return

    data = await state.get_data()
    game_type = data['game_type']
    
    balance = await get_balance(message.from_user.id)
    if balance < bet:
        await message.answer("❌ Недостаточно средств!")
        return
        
    await state.update_data(bet=bet)
    
    if game_type == "dice":
        await state.set_state(UserStates.dice_numbers)
        await state.update_data(selected_numbers=[])
        await message.answer(
            f"🎲 Ставка: {bet} Ежидзиков👍\n\nВыбери 3 числа (1-6):",
            reply_markup=dice_numbers_keyboard([])
        )
    elif game_type == "ejino":
        await message.answer(
            f"🦔 ЕЖИНО\n\nСтавка: {bet} Ежидзиков👍\n\nКрути и испытай удачу!",
            reply_markup=ejino_keyboard()
        )
        await state.set_state(None)
    elif game_type == "slots":
        await message.answer(
            f"🎰 Сл0ти|<И\n\nСтавка: {bet} Ежидзиков👍",
            reply_markup=slots_keyboard()
        )
        await state.set_state(None)
    elif game_type == "star":
        field = ["❌"] * 25
        star_positions = random.sample(range(25), 5)
        for pos in star_positions:
            field[pos] = "⭐"
        await state.update_data(field=field, revealed=[], total_win=0)
        await state.set_state(UserStates.star_game)
        await message.answer(
             f"🌟 Найди звезду!\n\nСтавка за нажатие: {bet} Ежидзиков👍\nВыигрыш: 0\n\nНажимай на ❓ чтобы открыть!",
             reply_markup=star_field_keyboard(field, [])
        )
    elif game_type == "x10":
        await message.answer(
             f"☠️ ×10 от ставки!\n\nСтавка: {bet} Ежидзиков👍\n\nТы уверен? Шанс всего 5%! 💀",
             reply_markup=x10_keyboard()
        )
        await state.set_state(None)


# 🦔 ЕЖИНО (рулетка)
@router.callback_query(F.data == "casino_ejino")
async def casino_ejino(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    
    await safe_edit_text(
        callback.message,
        f"🦔 ЕЖИНО — рулетка удачи!\n\n"
        f"Множители: ×0, ×0.5, ×1, ×1.5, ×2, ×5🔥\n"
        f"(×5 выпадает с шансом всего 8%!)\n\n"
        f"💰 Твой баланс: {user['balance']} Ежидзиков👍\n\n"
        f"Выбери ставку:",
        reply_markup=casino_bet_keyboard("ejino")
    )


@router.callback_query(F.data.startswith("bet_ejino_"), F.data != "bet_ejino_custom")
async def bet_ejino(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    bet = int(callback.data.replace("bet_ejino_", ""))
    balance = await get_balance(callback.from_user.id)
    
    if balance < bet:
        await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
        return
    
    await state.update_data(bet=bet)
    await safe_edit_text(
        callback.message,
        f"🦔 ЕЖИНО\n\n"
        f"Ставка: {bet} Ежидзиков👍\n\n"
        f"Крути и испытай удачу!",
        reply_markup=ejino_keyboard()
    )


@router.callback_query(F.data == "ejino_spin")
async def ejino_spin(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('bet', 0)
    
    if not bet:
        await callback.answer("❌ Сначала выбери ставку!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    await state.clear()
    
    roll = random.randint(1, 100)
    cumulative = 0
    multiplier = 0
    
    for mult, chance in EJINO_MULTIPLIERS:
        cumulative += chance
        if roll <= cumulative:
            multiplier = mult
            break
    
    win = int(bet * multiplier)
    profit = win - bet
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (bet, user_id, bet))
        if cursor.rowcount == 0:
            await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
            return
        if win > 0:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
        
        if profit > 0:
            await db.execute(
                "UPDATE users SET casino_wins = casino_wins + 1, total_casino_profit = total_casino_profit + ? WHERE user_id = ?",
                (profit, user_id)
            )
        elif profit < 0:
            await db.execute(
                "UPDATE users SET casino_losses = casino_losses + 1, total_casino_profit = total_casino_profit + ? WHERE user_id = ?",
                (profit, user_id)
            )
        await db.commit()
    
    if multiplier == 5:
        emoji = "🔥🎉🔥"
    elif multiplier >= 2:
        emoji = "🎉"
    elif multiplier >= 1:
        emoji = "😐"
    else:
        emoji = "😔"
    
    await safe_edit_text(
        callback.message,
        f"🦔 ЕЖИНО крутится...\n\n"
        f"Результат: ×{multiplier} {emoji}\n\n"
        f"Ставка: {bet} → Выигрыш: {win} Ежидзиков👍",
        reply_markup=back_button("casino")
    )


# 🎰 СЛОТЫ
@router.callback_query(F.data == "casino_slots")
async def casino_slots(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    
    await safe_edit_text(
        callback.message,
        f"🎰 Сл0ти|<И\n\n"
        f"3 разных эмодзи = ×0 (потеря ставки)\n"
        f"2 одинаковых = ×1.3\n"
        f"3 одинаковых = ×2.5\n\n"
        f"💰 Твой баланс: {user['balance']} Ежидзиков👍\n\n"
        f"Выбери ставку:",
        reply_markup=casino_bet_keyboard("slots")
    )


@router.callback_query(F.data.startswith("bet_slots_"), F.data != "bet_slots_custom")
async def bet_slots(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    bet = int(callback.data.replace("bet_slots_", ""))
    balance = await get_balance(callback.from_user.id)
    
    if balance < bet:
        await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
        return
    
    await state.update_data(bet=bet)
    await safe_edit_text(
        callback.message,
        f"🎰 Сл0ти|<И\n\n"
        f"Ставка: {bet} Ежидзиков👍",
        reply_markup=slots_keyboard()
    )


@router.callback_query(F.data == "slots_spin")
async def slots_spin(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('bet', 0)
    
    if not bet:
        await callback.answer("❌ Сначала выбери ставку!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    await state.clear()
    
    result = [random.choice(CASINO_EMOJI) for _ in range(3)]
    unique = len(set(result))
    
    if unique == 1:
        multiplier = 2.5
    elif unique == 2:
        multiplier = 1.3
    else:
        multiplier = 0
    
    win = int(bet * multiplier)
    profit = win - bet
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (bet, user_id, bet))
        if cursor.rowcount == 0:
            await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
            return
        if win > 0:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
        
        if profit > 0:
            await db.execute(
                "UPDATE users SET casino_wins = casino_wins + 1, total_casino_profit = total_casino_profit + ? WHERE user_id = ?",
                (profit, user_id)
            )
        elif profit < 0:
            await db.execute(
                "UPDATE users SET casino_losses = casino_losses + 1, total_casino_profit = total_casino_profit + ? WHERE user_id = ?",
                (profit, user_id)
            )
        await db.commit()
    
    if multiplier == 2.5:
        emoji = "🎉🎉🎉"
    elif multiplier == 1.3:
        emoji = "🎉"
    else:
        emoji = "😔"
    
    await safe_edit_text(
        callback.message,
        f"🎰 Крутим...\n\n"
        f"[ {result[0]} | {result[1]} | {result[2]} ]\n\n"
        f"Множитель: ×{multiplier} {emoji}\n"
        f"💰 Результат: {win} Ежидзиков👍",
        reply_markup=back_button("casino")
    )


# 🌟 НАЙДИ ЗВЕЗДУ (Updated v3.8 Logic)
@router.callback_query(F.data == "casino_star")
async def casino_star(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    
    await safe_edit_text(
        callback.message,
        f"🌟 Найди звезду!\n\n"
        f"Поле 5×5, в нём спрятано 5 звёзд ⭐\n"
        f"Нашёл звезду = ×2.5 от ставки\n"
        f"Не нашёл = ×0 (Потеря ставки)\n\n"
        f"Каждое нажатие стоит ставку!\n\n"
        f"💰 Твой баланс: {user['balance']} Ежидзиков👍\n\n"
        f"Выбери ставку за одно нажатие:",
        reply_markup=casino_bet_keyboard("star")
    )


@router.callback_query(F.data.startswith("bet_star_"), F.data != "bet_star_custom")
async def bet_star(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    bet = int(callback.data.replace("bet_star_", ""))
    balance = await get_balance(callback.from_user.id)
    
    if balance < bet:
        await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
        return
    
    field = ["❌"] * 25
    star_positions = random.sample(range(25), 5)
    for pos in star_positions:
        field[pos] = "⭐"
    
    await state.update_data(bet=bet, field=field, revealed=[], total_win=0)
    await state.set_state(UserStates.star_game)
    
    await safe_edit_text(
        callback.message,
        f"🌟 Найди звезду!\n\n"
        f"Ставка за нажатие: {bet} Ежидзиков👍\n"
        f"Выигрыш: 0 Ежидзиков👍\n\n"
        f"Нажимай на ❓ чтобы открыть!",
        reply_markup=star_field_keyboard(field, [])
    )


@router.callback_query(F.data.startswith("star_"), UserStates.star_game)
async def star_reveal(callback: CallbackQuery, state: FSMContext):
    if callback.data == "star_end":
        data = await state.get_data()
        total_win = data.get('total_win', 0)
        await state.clear()
        
        await safe_edit_text(
            callback.message,
            f"🌟 Игра окончена!\n\n"
            f"💰 Всего выиграно: {total_win} Ежидзиков👍",
            reply_markup=back_button("casino")
        )
        return
    
    idx = int(callback.data.replace("star_", ""))
    data = await state.get_data()
    
    bet = data['bet']
    field = data['field']
    revealed = data['revealed']
    total_win = data['total_win']
    user_id = callback.from_user.id
    
    if idx in revealed:
        await callback.answer("Уже открыто!")
        return
    
    revealed.append(idx)
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (bet, user_id, bet))
        if cursor.rowcount == 0:
            await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
            return
        await db.commit()
    
    if field[idx] == "⭐":
        win = int(bet * 2.5)
        total_win += win
        await update_balance(user_id, win)
        await callback.answer(f"🌟 ЗВЕЗДА! +{win} Ежидзиков👍!", show_alert=True)
    else:
        win = 0 # Loss in v3.8
        await callback.answer(f"❌ Пусто! Ты потерял {bet} Ежидзиков👍", show_alert=True)
    
    await state.update_data(revealed=revealed, total_win=total_win)
    
    new_balance = await get_balance(user_id)
    
    await safe_edit_text(
        callback.message,
        f"🌟 Найди звезду!\n\n"
        f"Ставка за нажатие: {bet} Ежидзиков👍\n"
        f"Выигрыш: {total_win} Ежидзиков👍\n"
        f"💰 Баланс: {new_balance} Ежидзиков👍\n\n"
        f"Нажимай на ❓ чтобы открыть!",
        reply_markup=star_field_keyboard(field, revealed)
    )

@router.callback_query(F.data == "star_end", UserStates.star_game)
async def star_end_direct(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    total_win = data.get('total_win', 0)
    await state.clear()
    
    await safe_edit_text(
        callback.message,
        f"🌟 Игра окончена!\n\n"
        f"💰 Всего выиграно: {total_win} Ежидзиков👍",
        reply_markup=back_button("casino")
    )


# ☠️ ×10 ОТ СТАВКИ
@router.callback_query(F.data == "casino_x10")
async def casino_x10(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    
    await safe_edit_text(
        callback.message,
        f"☠️ ×10 от ставки!\n\n"
        f"Шанс победы: всего 5%!\n"
        f"Победа = ×10 от ставки 🔥\n"
        f"Проигрыш = теряешь ставку 💀\n\n"
        f"💰 Твой баланс: {user['balance']} Ежидзиков👍\n\n"
        f"Выбери ставку:",
        reply_markup=casino_bet_keyboard("x10")
    )


@router.callback_query(F.data.startswith("bet_x10_"), F.data != "bet_x10_custom")
async def bet_x10(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    bet = int(callback.data.replace("bet_x10_", ""))
    balance = await get_balance(callback.from_user.id)
    
    if balance < bet:
        await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
        return
    
    await state.update_data(bet=bet)
    await safe_edit_text(
        callback.message,
        f"☠️ ×10 от ставки!\n\n"
        f"Ставка: {bet} Ежидзиков👍\n\n"
        f"Ты уверен? Шанс всего 5%! 💀",
        reply_markup=x10_keyboard()
    )


@router.callback_query(F.data == "x10_try")
async def x10_try(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('bet', 0)
    
    if not bet:
        await callback.answer("❌ Сначала выбери ставку!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    await state.clear()
    
    if random.random() < 0.05:
        win = bet * 10
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (bet, user_id, bet))
            if cursor.rowcount == 0:
                await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
                return
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, user_id))
            await db.execute(
                "UPDATE users SET casino_wins = casino_wins + 1, total_casino_profit = total_casino_profit + ? WHERE user_id = ?",
                (win - bet, user_id)
            )
            await db.commit()
        
        await safe_edit_text(
            callback.message,
            f"☠️ НЕВЕРОЯТНО! 🔥🎉🔥\n\n"
            f"ТЫ ВЫИГРАЛ ×10!!!\n"
            f"💰 +{win} Ежидзиков👍!",
            reply_markup=back_button("casino")
        )
    else:
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (bet, user_id, bet))
            if cursor.rowcount == 0:
                await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
                return
            await db.execute(
                "UPDATE users SET casino_losses = casino_losses + 1, total_casino_profit = total_casino_profit - ? WHERE user_id = ?",
                (bet, user_id)
            )
            await db.commit()
        
        await safe_edit_text(
            callback.message,
            f"☠️ Не повезло... 💀\n\n"
            f"💸 -{bet} Ежидзиков👍",
            reply_markup=back_button("casino")
        )

# =====================================
# 🎁 БОНУСЫ
# =====================================

@router.callback_query(F.data == "bonuses")
async def bonuses(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(
        callback.message,
        "🎁 Здесь ты можешь получить все бонусы доступные в боте! 🎁\n\n"
        "📺 Реклама: просмотр картинок ежа и плата за это прямо на баланс!\n\n"
        "📤 Выставить рекламу за 70 ежидзиков👍: пришлите фото ежа 🦔, и ваша реклама появится!",
        reply_markup=bonuses_keyboard(),
        media_screen="bonuses"
    )


@router.callback_query(F.data == "daily_bonus")
async def daily_bonus(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await callback.answer("Ошибка! Попробуй /start", show_alert=True)
        return
    
    now = datetime.now()
    last_daily = user['last_daily']
    
    if last_daily:
        try:
            last_daily_dt = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S")
            if now - last_daily_dt < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_daily_dt)
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                await callback.answer(f"⏰ Следующий бонус через {hours}ч {minutes}мин", show_alert=True)
                return
        except:
            pass
            
    bonus_amount = int(await get_setting("daily_bonus", "25"))
    await update_balance(user_id, bonus_amount)
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET last_daily = ? WHERE user_id = ?",
            (now.strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        await db.commit()
    
    await callback.answer(f"🎁 +{bonus_amount} Ежидзиков👍!", show_alert=True)
    await safe_edit_text(
        callback.message,
        f"🎁 Ежедневный бонус получен!\n\n"
        f"+{bonus_amount} Ежидзиков👍\n\n"
        "Приходи завтра за новым бонусом!",
        reply_markup=back_button("bonuses")
    )


@router.callback_query(F.data == "submit_ad")
async def submit_ad(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    if await check_shadow_ban(callback.from_user.id, "ban_ads"):
        await callback.answer("🚫 Вам запрещено подавать рекламу!", show_alert=True)
        return
        
    user_id = callback.from_user.id
    balance = await get_balance(user_id)
    
    if balance < 70:
        await callback.answer("❌ Недостаточно Ежидзиков! Нужно 70.", show_alert=True)
        return
    
    await state.set_state(UserStates.waiting_ad_photo)
    await safe_edit_text(
        callback.message,
        "📤 Отправь фото ежа 🦔 для рекламы:\n\n"
        "Стоимость: 70 Ежидзиков👍",
        reply_markup=back_button("bonuses")
    )


@router.message(UserStates.waiting_ad_photo, F.photo)
async def process_ad_photo(message: Message, state: FSMContext):
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("UPDATE users SET balance = balance - 70 WHERE user_id = ? AND balance >= 70", (user_id,))
        if cursor.rowcount == 0:
            await message.answer("❌ Недостаточно Ежидзиков! Нужно 70.")
            await state.clear()
            return
        await db.commit()
    
    file_id = message.photo[-1].file_id
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            INSERT INTO ads (user_id, file_id, status, created_at)
            VALUES (?, ?, 'pending', ?)
        ''', (user_id, file_id, created_at))
        ad_id = cursor.lastrowid
        await db.commit()
    
    admins = await get_all_admins()
    for admin in admins:
        try:
            if admin['user_id']:
                await bot.send_photo(
                    admin['user_id'],
                    file_id,
                    caption=f"🖼 Новая реклама на модерацию\n\nОт: @{message.from_user.username or 'Unknown'} (ID: {user_id})",
                    reply_markup=ad_moderation_keyboard(ad_id)
                )
        except:
            pass
    
    await state.clear()
    is_user_admin = await is_admin(user_id)
    await message.answer(
        "✅ Реклама отправлена на модерацию!\n\n"
        "Ты получишь уведомление когда админ её проверит.",
        reply_markup=main_menu_keyboard(is_user_admin)
    )


@router.callback_query(F.data == "watch_ad")
async def watch_ad(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await callback.answer("Ошибка! Попробуй /start", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ads WHERE status = 'approved'") as cursor:
            ads = await cursor.fetchall()
    
    if not ads:
        await callback.answer("😔 Пока нет рекламы для просмотра", show_alert=True)
        return
    
    ad_index = user['ad_index'] % len(ads)
    ad = ads[ad_index]
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ad_index = ? WHERE user_id = ?", (ad_index + 1, user_id))
        await db.commit()
    
    await safe_delete(callback.message)
    
    sent_msg = await callback.message.answer_photo(
        ad['file_id'],
        caption="📺 Смотри рекламу 10 секунд..."
    )
    
    await asyncio.sleep(10)
    
    reward = 3
    if user['double_ad_until']:
        try:
            double_until = datetime.strptime(user['double_ad_until'], "%Y-%m-%d %H:%M:%S")
            if datetime.now() < double_until:
                reward = 6
        except:
            pass
    
    # Golden Hedgehog Bonus
    if user['hedgehog_class'] == 'golden':
        reward *= 2

    await update_balance(user_id, reward)
    balance = await get_balance(user_id)
    
    await safe_delete(sent_msg)
    
    await callback.message.answer(
        f"✅ Реклама просмотрена!\n\n"
        f"+{reward} Ежидзиков👍\n"
        f"💰 Баланс: {balance} Ежидзиков👍",
        reply_markup=bonuses_keyboard()
    )


# =====================================
# 🛒 МАГАЗИН
# =====================================

@router.callback_query(F.data == "shop")
async def shop_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    is_user_admin = await is_admin(callback.from_user.id)
    
    await safe_edit_text(
        callback.message,
        "🛒Твой ёж захотел в магазин! 🛒\n"
        "🛒 Здесь ты можешь что нибудь прикупить!",
        reply_markup=shop_keyboard(is_user_admin),
        media_screen="shop"
    )


@router.callback_query(F.data == "shop_list")
async def shop_list(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    # Sorting logic: items priced in SKIN (currency='skin') are multiplied by 45 for sorting
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM shop_items 
            ORDER BY CASE WHEN currency='skin' THEN price * 45 ELSE price END ASC
        ''') as cursor:
            items = await cursor.fetchall()
    
    if not items:
        await callback.answer("😔 Магазин пуст!", show_alert=True)
        return
    
    await show_shop_item(callback.message, items, 0)


async def show_shop_item(message: Message, items: list, index: int):
    item = items[index]
    currency_label = "Ежидзиков👍"
    if item['currency'] == 'skin':
        currency_label = "Кожи слона🐘"
    elif item['currency'] == 'diamonds':
        currency_label = "Алмазов💎"
        
    price_text = f"{item['price']} {currency_label}" if item['price'] > 0 else "Бесплатно!"
    
    await safe_edit_text(
        message,
        f"🛒 {item['name']}\n\n"
        f"💰 Цена: {price_text}\n\n"
        f"📦 Товар {index + 1} из {len(items)}",
        reply_markup=shop_item_keyboard(index, len(items))
    )

@router.callback_query(F.data.startswith("shop_item_"))
async def shop_item_navigate(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    item_index = int(callback.data.replace("shop_item_", ""))
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM shop_items 
            ORDER BY CASE WHEN currency='skin' THEN price * 45 ELSE price END ASC
        ''') as cursor:
            items = await cursor.fetchall()
    
    if not items:
        await callback.answer("😔 Магазин пуст!", show_alert=True)
        return
    
    item_index = item_index % len(items)
    await show_shop_item(callback.message, items, item_index)


@router.callback_query(F.data.startswith("buy_item_"))
async def buy_item(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    item_index = int(callback.data.replace("buy_item_", ""))
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM shop_items 
            ORDER BY CASE WHEN currency='skin' THEN price * 45 ELSE price END ASC
        ''') as cursor:
            items = await cursor.fetchall()
        
        if not items or item_index >= len(items):
            await callback.answer("❌ Товар не найден!", show_alert=True)
            return
        
        item = items[item_index]
        
        # Проверка валюты
        if item['currency'] == 'skin':
            balance = await get_elephant_skin(user_id)
            if balance < item['price']:
                await callback.answer(f"❌ Недостаточно Кожи слона! Нужно {item['price']}", show_alert=True)
                return
            if item['price'] > 0:
                await db.execute("UPDATE users SET elephant_skin = elephant_skin - ? WHERE user_id = ?", (item['price'], user_id))
        elif item['currency'] == 'diamonds':
            user = await get_user(user_id)
            if user['diamonds'] < item['price']:
                await callback.answer(f"❌ Недостаточно Алмазов! Нужно {item['price']}", show_alert=True)
                return
            if item['price'] > 0:
                 await db.execute("UPDATE users SET diamonds = diamonds - ? WHERE user_id = ?", (item['price'], user_id))
        else: # balance
            balance = await get_balance(user_id)
            if balance < item['price']:
                await callback.answer(f"❌ Недостаточно Ежидзиков! Нужно {item['price']}", show_alert=True)
                return
            if item['price'] > 0:
                await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (item['price'], user_id))
        
        # Check if already own (can buy multiple if consumable? Logic says inventory allows stacks)
        # Check max stack? Let's say max 100 per item to prevent db bloat/lag
        async with db.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item['id'])) as cursor:
            row = await cursor.fetchone()
            if row and row[0] >= 100:
                await callback.answer("❌ Слишком много предметов этого типа!", show_alert=True)
                # Rollback currency? The transaction hasn't committed yet.
                # Just return (no commit happens if we don't proceed)
                return 

        await db.execute('''
            INSERT INTO inventory (user_id, item_id, quantity, total_spent)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET
                quantity = quantity + 1,
                total_spent = total_spent + ?
        ''', (user_id, item['id'], item['price'], item['price']))
        await db.commit()
    
    await callback.answer(f"✅ Куплено: {item['name']}!", show_alert=True)
    
    user = await get_user(user_id)
    currency_label = "Ежидзиков👍"
    bal_display = user['balance']
    if item['currency'] == 'skin':
        currency_label = "Кожи слона🐘"
        bal_display = user['elephant_skin']
    elif item['currency'] == 'diamonds':
        currency_label = "Алмазов💎"
        bal_display = user['diamonds']

    price_text = f"{item['price']} {currency_label}" if item['price'] > 0 else "Бесплатно!"
    
    await safe_edit_text(
        callback.message,
        f"🛒 {item['name']}\n\n"
        f"💰 Цена: {price_text}\n"
        f"💳 Твой баланс: {bal_display} {currency_label}\n\n"
        f"📦 Товар {item_index + 1} из {len(items)}",
        reply_markup=shop_item_keyboard(item_index, len(items))
    )


# =====================================
# 📚 БИБЛИОТЕКА (v3.8)
# =====================================

@router.callback_query(F.data == "book_menu")
async def book_menu(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback): return
    if await check_shadow_ban(callback.from_user.id, "ban_books"):
         await callback.answer("🚫 Вам запрещен доступ к библиотеке!", show_alert=True)
         return

    await safe_edit_text(
        callback.message,
        "📚 Библиотека ежей\n\nЗдесь можно написать свою книгу и продать её за Кожу Слона, или купить шедевры других ежей!",
        reply_markup=book_menu_keyboard()
    )

@router.callback_query(F.data == "write_book")
async def write_book_start(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback): return
    await state.set_state(UserStates.book_title)
    await safe_edit_text(callback.message, "✍️ Введите название книги:", reply_markup=back_button("book_menu"))

@router.message(UserStates.book_title)
async def book_title_input(message: Message, state: FSMContext):
    if not await check_access(bot, message.from_user.id, message=message): return
    await state.update_data(title=message.text)
    await state.set_state(UserStates.book_text)
    await message.answer("✍️ Введите текст книги (содержание):")

@router.message(UserStates.book_text)
async def book_text_input(message: Message, state: FSMContext):
    if not await check_access(bot, message.from_user.id, message=message): return
    await state.update_data(content=message.text)
    await state.set_state(UserStates.book_price)
    await message.answer("✍️ Укажите цену книги (в Коже Слона 🐘):")

@router.message(UserStates.book_price)
async def book_price_input(message: Message, state: FSMContext):
    if not await check_access(bot, message.from_user.id, message=message): return
    try:
        price = int(message.text)
        if price < 0: raise ValueError
    except:
        await message.answer("❌ Введите положительное число!")
        return

    data = await state.get_data()
    user = await get_user(message.from_user.id)
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            INSERT INTO books (author_id, author_username, title, content, price, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        ''', (user['user_id'], user['username'], data['title'], data['content'], price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        book_id = cursor.lastrowid
        await db.commit()
    
    await state.clear()
    await message.answer("✅ Книга отправлена на модерацию!", reply_markup=shop_keyboard(await is_admin(user['user_id'])))
    
    # Notify admins
    admins = await get_all_admins()
    for admin in admins:
        try:
            await bot.send_message(
                admin['user_id'],
                f"📚 Новая книга на модерацию!\n\n"
                f"Название: {data['title']}\n"
                f"Автор: @{user['username']}\n"
                f"Цена: {price} Кожи\n"
                f"Текст: {data['content'][:100]}...",
                reply_markup=book_mod_keyboard(book_id)
            )
        except: pass

@router.callback_query(F.data == "buy_books")
async def buy_books_list(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback): return
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM books WHERE status = 'approved'") as cursor:
            books = await cursor.fetchall()
            
    if not books:
        await callback.answer("📚 Книг в продаже нет.", show_alert=True)
        return
        
    # Simple list showing first available (can be paginated but keeping simple for now)
    book = books[0]
    await safe_edit_text(
        callback.message,
        f"📚 {book['title']}\n"
        f"👤 Автор: @{book['author_username']}\n"
        f"💰 Цена: {book['price']} Кожи слона🐘",
        reply_markup=book_buy_keyboard(book['id'])
    )

@router.callback_query(F.data.startswith("purchase_book_"))
async def purchase_book(callback: CallbackQuery):
    book_id = int(callback.data.replace("purchase_book_", ""))
    user_id = callback.from_user.id
    
    # Race Condition Protection for Purchases (Double check status)
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM books WHERE id = ?", (book_id,)) as cursor:
            book = await cursor.fetchone()
            
        if not book or book['status'] != 'approved':
            await callback.answer("❌ Книга уже продана или недоступна.", show_alert=True)
            return
            
        skin = await get_elephant_skin(user_id)
        if skin < book['price']:
            await callback.answer(f"❌ Нужно {book['price']} Кожи слона!", show_alert=True)
            return
            
        # Transaction
        await db.execute("UPDATE users SET elephant_skin = elephant_skin - ? WHERE user_id = ?", (book['price'], user_id))
        await db.execute("UPDATE users SET elephant_skin = elephant_skin + ? WHERE user_id = ?", (book['price'], book['author_id']))
        
        # Golden Hedgehog Author Bonus
        author = await get_user(book['author_id'])
        if author and author['hedgehog_class'] == 'golden':
             await db.execute("UPDATE users SET balance = balance + 10 WHERE user_id = ?", (book['author_id'],))

        await db.execute("UPDATE books SET status = 'sold' WHERE id = ?", (book_id,))
        await db.commit()
        
    await bot.send_message(user_id, f"📖 Вы купили книгу «{book['title']}»:\n\n{book['content']}")
    await callback.message.answer("✅ Книга куплена и отправлена вам в ЛС!")


# =====================================
# 👾 ИНВЕНТАРЬ
# =====================================

@router.callback_query(F.data == "inventory")
async def inventory_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT i.*, s.name, s.price, s.currency FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0
            ORDER BY s.name
        ''', (user_id,)) as cursor:
            items = await cursor.fetchall()
    
    if not items:
        await safe_edit_text(
            callback.message,
            "👾 Твой инвентарь пуст!\n\n"
            "Купи что-нибудь в магазине!",
            reply_markup=back_button("shop")
        )
        return
    
    item = items[0]
    
    await safe_edit_text(
        callback.message,
        f"👾 {item['name']}\n\n"
        f"📦 Количество: {item['quantity']} шт.\n"
        f"💰 Потрачено: {item['total_spent']} {CURRENCY_LABELS.get(item['currency'], item['currency'])}\n\n"
        f"🎒 Предмет 1 из {len(items)}",
        reply_markup=inventory_keyboard(0, len(items), item['name'], user['is_injured'])
    )


@router.callback_query(F.data.startswith("inv_item_"))
async def inventory_navigate(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    item_index = int(callback.data.replace("inv_item_", ""))
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT i.*, s.name, s.price, s.currency FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0
            ORDER BY s.name
        ''', (user_id,)) as cursor:
            items = await cursor.fetchall()
    
    if not items:
        await safe_edit_text(
            callback.message,
            "👾 Твой инвентарь пуст!",
            reply_markup=back_button("shop")
        )
        return
    
    item_index = item_index % len(items)
    item = items[item_index]
    
    await safe_edit_text(
        callback.message,
        f"👾 {item['name']}\n\n"
        f"📦 Количество: {item['quantity']} шт.\n"
        f"💰 Потрачено: {item['total_spent']} {CURRENCY_LABELS.get(item['currency'], item['currency'])}\n\n"
        f"🎒 Предмет {item_index + 1} из {len(items)}",
        reply_markup=inventory_keyboard(item_index, len(items), item['name'], user['is_injured'])
    )


@router.callback_query(F.data.startswith("heal_hand_"))
async def heal_hand(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    item_index = int(callback.data.replace("heal_hand_", ""))
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if not user['is_injured']:
        await callback.answer("✅ Твоя рука уже здорова!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT i.*, s.name, s.price FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0 AND s.name LIKE '%Аптечка%'
            ORDER BY s.name
        ''', (user_id,)) as cursor:
            med_item = await cursor.fetchone()
    
    if not med_item or med_item['quantity'] <= 0:
        await callback.answer("❌ У тебя нет аптечки!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_injured = 0 WHERE user_id = ?", (user_id,))
        await db.execute(
            "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
            (user_id, med_item['item_id'])
        )
        await db.commit()
    
    await callback.answer("💊 Рука вылечена! Теперь можешь гладить ежа!", show_alert=True)
    
    # Show inventory at the same index instead of calling inventory_navigate (which would crash on callback.data parsing)
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT i.*, s.name, s.price, s.currency FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0
            ORDER BY s.name
        ''', (user_id,)) as cursor:
            items = await cursor.fetchall()
    
    if not items:
        await safe_edit_text(callback.message, "👾 Твой инвентарь пуст!", reply_markup=back_button("shop"))
    else:
        item_index = item_index % len(items)
        item = items[item_index]
        user = await get_user(user_id)
        await safe_edit_text(
            callback.message,
            f"👾 {item['name']}\n\n"
            f"📦 Количество: {item['quantity']} шт.\n"
            f"💰 Потрачено: {item['total_spent']} {CURRENCY_LABELS.get(item['currency'], item['currency'])}\n\n"
            f"🎒 Предмет {item_index + 1} из {len(items)}",
            reply_markup=inventory_keyboard(item_index, len(items), item['name'], user['is_injured'])
        )


@router.callback_query(F.data.startswith("sell_item_"))
async def sell_item_confirm(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    item_index = int(callback.data.replace("sell_item_", ""))
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT i.*, s.name, s.price, s.currency FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0
            ORDER BY s.name
        ''', (user_id,)) as cursor:
            items = await cursor.fetchall()
    
    if not items or item_index >= len(items):
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return
    
    item = items[item_index]
    
    if item['price'] == 0:
        await callback.answer("❌ Бесплатные товары нельзя продать!", show_alert=True)
        return
    
    sell_price = item['price'] // 2
    currency = "Ежидзиков👍"
    if item['currency'] == 'skin': currency = "Кожи слона🐘"
    elif item['currency'] == 'diamonds': currency = "Алмазов💎"
    
    await safe_edit_text(
        callback.message,
        f"💸 Продать {item['name']}?\n\n"
        f"⚠️ При продаже возвращается 50% цены!\n\n"
        f"💰 Ты получишь: {sell_price} {currency}",
        reply_markup=sell_confirm_keyboard(item_index)
    )


@router.callback_query(F.data.startswith("confirm_sell_"))
async def confirm_sell(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    item_index = int(callback.data.replace("confirm_sell_", ""))
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT i.*, s.name, s.price, s.currency FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0
            ORDER BY s.name
        ''', (user_id,)) as cursor:
            items = await cursor.fetchall()
    
    if not items or item_index >= len(items):
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return
    
    item = items[item_index]
    sell_price = item['price'] // 2
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
            (user_id, item['item_id'])
        )
        if item['currency'] == 'skin':
             await db.execute("UPDATE users SET elephant_skin = elephant_skin + ? WHERE user_id = ?", (sell_price, user_id))
        elif item['currency'] == 'diamonds':
             await db.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (sell_price, user_id))
        else:
             await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (sell_price, user_id))
        await db.commit()
    
    await callback.answer(f"✅ Продано! +{sell_price}", show_alert=True)
    
    # Refresh inventory view
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT i.*, s.name, s.price, s.currency FROM inventory i
            JOIN shop_items s ON i.item_id = s.id
            WHERE i.user_id = ? AND i.quantity > 0
            ORDER BY s.name
        ''', (user_id,)) as cursor:
            items = await cursor.fetchall()
            
    if not items:
         await safe_edit_text(
            callback.message,
            "👾 Твой инвентарь пуст!",
            reply_markup=back_button("shop")
        )
         return
    
    new_index = min(item_index, len(items)-1)
    user = await get_user(user_id)
    
    item = items[new_index]
    await safe_edit_text(
        callback.message,
        f"👾 {item['name']}\n\n"
        f"📦 Количество: {item['quantity']} шт.\n"
        f"💰 Потрачено: {item['total_spent']} {CURRENCY_LABELS.get(item['currency'], item['currency'])}\n\n"
        f"🎒 Предмет {new_index + 1} из {len(items)}",
        reply_markup=inventory_keyboard(new_index, len(items), item['name'], user['is_injured'])
    )


# =====================================
# 🤔 ТЕХПОДДЕРЖКА
# =====================================

@router.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    is_main = await is_main_admin(callback.from_user.id)
    await safe_edit_text(callback.message, "🦔🦔🦔", reply_markup=support_keyboard(is_main), media_screen="support")


@router.callback_query(F.data == "reset_username")
async def reset_username_handler(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    new_username = callback.from_user.username or "Unknown"
    await update_username(user_id, new_username)
    await callback.answer(f"✅ Username обновлён на @{new_username}!", show_alert=True)

@router.callback_query(F.data == "support_inline_info")
async def support_inline_info(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    text = (
        "ℹ️ **Информация об Inline режиме**\n\n"
        "Вы можете делиться промокодами через inline-режим бота!\n\n"
        "1. Введите в любом чате: `@bot pr CODE`\n"
        "(где CODE - код промокода)\n"
        "2. Появится кнопка **👍 Нажми СЮДА!**\n"
        "3. Отправьте сообщение, и любой пользователь сможет активировать промокод, нажав **🔥 Забрать**."
    )
    await safe_edit_text(callback.message, text, reply_markup=back_button("support"))


@router.callback_query(F.data == "policy_usage")
async def policy_usage(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(
        callback.message,
        "📜 Политика использования бота «🦔Говорящий Еж🦔»\n\n"
        "1. Бот создан для развлечения. Виртуальная валюта «Ежидзики» не имеет реальной ценности.\n\n"
        "2. Запрещено:\n"
        "   • Использовать ботов/скрипты для накрутки\n"
        "   • Спамить в техподдержку\n"
        "   • Злоупотреблять багами (о них нужно сообщать)\n"
        "   • Оскорблять других пользователей\n\n"
        "3. Администрация может:\n"
        "   • Обнулить баланс нарушителям\n"
        "   • Заблокировать доступ к боту\n"
        "   • Изменять правила без предупреждения\n\n"
        "4. Используя бота, вы соглашаетесь с этими правилами.\n\n"
        "🦔 Приятной игры!",
        reply_markup=back_button("support")
    )


@router.callback_query(F.data == "policy_privacy")
async def policy_privacy(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await safe_edit_text(
        callback.message,
        "🔒 Политика конфиденциальности бота «🦔Говорящий Еж🦔»\n\n"
        "1. Какие данные мы собираем:\n"
        "   • Ваш Telegram ID и username\n"
        "   • Игровую статистику (баланс, покупки, действия)\n"
        "   • Сообщения в техподдержку\n\n"
        "2. Как используем данные:\n"
        "   • Для работы бота и сохранения прогресса\n"
        "   • Для ответов на обращения\n"
        "   • Для формирования топов игроков\n\n"
        "3. Мы НЕ передаём данные третьим лицам.\n\n"
        "4. Данные хранятся на защищённом сервере.\n\n"
        "5. Вы можете запросить удаление данных через техподдержку.\n\n"
        "🦔 Ваша безопасность важна для нас!",
        reply_markup=back_button("support")
    )


@router.callback_query(F.data == "write_support")
async def write_support(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await state.set_state(UserStates.waiting_support_message)
    await safe_edit_text(
        callback.message,
        "🆘 Напиши своё сообщение в техподдержку:\n\n"
        "Можешь прикрепить фото или видео.",
        reply_markup=back_button("support")
    )


@router.message(UserStates.waiting_support_message)
async def process_support_message(message: Message, state: FSMContext):
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    await update_username(user_id, username)
    
    message_text = message.text or message.caption or ""
    media_type = None
    media_file_id = None
    
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    if not message_text and not media_file_id:
        await message.answer("❌ Отправь текст, фото или видео!")
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            INSERT INTO support_tickets (user_id, username, message_text, media_type, media_file_id, ticket_type, created_at)
            VALUES (?, ?, ?, ?, ?, 'support', ?)
        ''', (user_id, username, message_text, media_type, media_file_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ticket_id = cursor.lastrowid
        await db.commit()
    
    admins = await get_all_admins()
    for admin in admins:
        try:
            if admin['user_id']:
                caption = f"🆘 Новое обращение в техподдержку\n\nОт: @{username} (ID: {user_id})\n\n{message_text}"
                if media_type == "photo":
                    await bot.send_photo(admin['user_id'], media_file_id, caption=caption, reply_markup=support_ticket_keyboard(ticket_id))
                elif media_type == "video":
                    await bot.send_video(admin['user_id'], media_file_id, caption=caption, reply_markup=support_ticket_keyboard(ticket_id))
                else:
                    await bot.send_message(admin['user_id'], caption, reply_markup=support_ticket_keyboard(ticket_id))
        except:
            pass
    
    await state.clear()
    is_user_admin = await is_admin(user_id)
    await message.answer(
        "✅ Сообщение отправлено в техподдержку!\n\nОжидай ответа от админа.",
        reply_markup=main_menu_keyboard(is_user_admin)
    )
    
    # Bugfix return markup - removed dead return


@router.callback_query(F.data == "write_suggestion")
async def write_suggestion(callback: CallbackQuery, state: FSMContext):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    await state.set_state(UserStates.waiting_suggestion_message)
    await safe_edit_text(
        callback.message,
        "💫 Напиши своё предложение по обновлению:\n\n"
        "Можешь прикрепить фото или видео.",
        reply_markup=back_button("support")
    )


@router.message(UserStates.waiting_suggestion_message)
async def process_suggestion_message(message: Message, state: FSMContext):
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    await update_username(user_id, username)
    
    message_text = message.text or message.caption or ""
    media_type = None
    media_file_id = None
    
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    
    if not message_text and not media_file_id:
        await message.answer("❌ Отправь текст, фото или видео!")
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            INSERT INTO support_tickets (user_id, username, message_text, media_type, media_file_id, ticket_type, created_at)
            VALUES (?, ?, ?, ?, ?, 'suggestion', ?)
        ''', (user_id, username, message_text, media_type, media_file_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ticket_id = cursor.lastrowid
        await db.commit()
    
    admins = await get_all_admins()
    for admin in admins:
        try:
            if admin['user_id']:
                caption = f"💫 Новое предложение обновления\n\nОт: @{username} (ID: {user_id})\n\n{message_text}"
                if media_type == "photo":
                    await bot.send_photo(admin['user_id'], media_file_id, caption=caption, reply_markup=support_ticket_keyboard(ticket_id))
                elif media_type == "video":
                    await bot.send_video(admin['user_id'], media_file_id, caption=caption, reply_markup=support_ticket_keyboard(ticket_id))
                else:
                    await bot.send_message(admin['user_id'], caption, reply_markup=support_ticket_keyboard(ticket_id))
        except:
            pass
    
    await state.clear()
    is_user_admin = await is_admin(user_id)
    await message.answer(
        "✅ Предложение отправлено!\n\nОжидай ответа от админа.",
        reply_markup=main_menu_keyboard(is_user_admin)
    )


@router.callback_query(F.data == "super_reset")
async def super_reset_confirm(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        await callback.answer("❌ Только главный админ!", show_alert=True)
        return
    
    await safe_edit_text(
        callback.message,
        "☢️ ВНИМАНИЕ! ☢️\n\n"
        "Ты собираешься ПОЛНОСТЬЮ очистить базу данных!\n\n"
        "❌ Все пользователи будут удалены\n"
        "❌ Все балансы обнулятся\n"
        "❌ Все товары, инвентарь, реклама - ВСЁ удалится!\n\n"
        "ЭТО ДЕЙСТВИЕ НЕЛЬЗЯ ОТМЕНИТЬ!\n\n"
        "Ты уверен?",
        reply_markup=confirm_super_reset_keyboard()
    )


@router.callback_query(F.data == "confirm_super_reset")
async def confirm_super_reset(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        await callback.answer("❌ Только главный админ!", show_alert=True)
        return
    
    await safe_edit_text(callback.message, "☢️ Очистка базы данных... Подожди...")
    
    user_ids = await reset_database()
    
    success = 0
    for uid in user_ids:
        try:
            await bot.send_message(
                uid,
                "🦔 Бот полностью очищен! 🦔\n\n"
                "Все данные сброшены. Нажми /start чтобы начать заново!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Начать заново", callback_data="check_subscription")]
                ])
            )
            success += 1
        except:
            pass
    
    await ensure_main_admin(callback.from_user.username)
    
    await safe_edit_text(
        callback.message,
        f"☢️ БАЗА ДАННЫХ ОЧИЩЕНА! ☢️\n\n"
        f"📢 Уведомлено пользователей: {success}/{len(user_ids)}\n\n"
        f"Нажми /start чтобы начать заново.",
        reply_markup=back_button("menu")
    )

# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - ЧАСТЬ 4B/5 🦔
# =====================================
# Админ-панель (AdminOS v3.8)

# =====================================
# 🛠 АДМИН-ПАНЕЛЬ
# =====================================

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    # Открываем главное меню AdminOS
    await safe_edit_text(
        callback.message, 
        "💻 **Hedgehog AdminOS**\nВыберите категорию:", 
        reply_markup=admin_main_keyboard(),
        parse_mode="Markdown"
    )

# --- FOLDERS ---

@router.callback_query(F.data == "admin_folder_players")
async def admin_folder_players(callback: CallbackQuery):
    await safe_edit_text(callback.message, "📂 **AdminOS / Игроки**", reply_markup=admin_players_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_folder_marketing")
async def admin_folder_marketing(callback: CallbackQuery):
    await safe_edit_text(callback.message, "📂 **AdminOS / Маркетинг**", reply_markup=admin_marketing_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_folder_content")
async def admin_folder_content(callback: CallbackQuery):
    await safe_edit_text(callback.message, "📂 **AdminOS / Контент**", reply_markup=admin_content_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_folder_settings")
async def admin_folder_settings(callback: CallbackQuery):
    is_main = await is_main_admin(callback.from_user.id)
    await safe_edit_text(callback.message, "📂 **AdminOS / Настройки**", reply_markup=admin_settings_keyboard(is_main), parse_mode="Markdown")

# --- STATS ---

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        
        today = datetime.now().strftime("%Y-%m-%d")
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM stats WHERE timestamp LIKE ?", (f"{today}%",)) as cursor:
            active_today = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COUNT(*) FROM promocodes") as cursor:
            total_promos = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COALESCE(SUM(total_uses), 0) FROM promocodes") as cursor:
            total_activations = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COALESCE(SUM(balance), 0), COALESCE(SUM(diamonds), 0) FROM users") as cursor:
            eco_stats = await cursor.fetchone()
            total_balance = eco_stats[0]
            total_diamonds = eco_stats[1]
        
        async with db.execute("SELECT COALESCE(SUM(ants), 0) FROM users") as cursor:
            total_ants = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COUNT(*) FROM ads WHERE status = 'approved'") as cursor:
            total_ads = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COUNT(*) FROM ads WHERE status = 'pending'") as cursor:
            pending_ads = (await cursor.fetchone())[0]
        
        async with db.execute("SELECT COALESCE(SUM(casino_wins), 0), COALESCE(SUM(casino_losses), 0), COALESCE(SUM(total_casino_profit), 0) FROM users") as cursor:
            casino_stats = await cursor.fetchone()
    
    await safe_edit_text(
        callback.message,
        f"📊 Статистика бота\n\n"
        f"👥 Всего игроков: {total_users}\n"
        f"📅 Активных сегодня: {active_today}\n"
        f"🎟 Всего промокодов: {total_promos}\n"
        f"✅ Всего активаций: {total_activations}\n"
        f"💰 Ежидзиков: {total_balance}\n"
        f"💎 Алмазов: {total_diamonds}\n"
        f"🐜 Всего муравьёв: {total_ants}\n"
        f"🖼 Одобренной рекламы: {total_ads}\n"
        f"⏳ На модерации: {pending_ads}\n\n"
        f"🎰 Казино:\n"
        f"   Побед: {casino_stats[0]}\n"
        f"   Поражений: {casino_stats[1]}\n"
        f"   Общий профит игроков: {casino_stats[2]}",
        reply_markup=back_button("admin_panel")
    )


# =====================================
# 📢 РАССЫЛКА
# =====================================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await safe_edit_text(
        callback.message,
        "📢 Рассылка сообщений\n\n"
        "Выбери какому проценту пользователей отправить:",
        reply_markup=broadcast_percent_keyboard()
    )


@router.callback_query(F.data.startswith("broadcast_"))
async def broadcast_select_percent(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    percent = int(callback.data.replace("broadcast_", ""))
    await state.update_data(broadcast_percent=percent)
    await state.set_state(AdminStates.waiting_broadcast_message)
    
    await safe_edit_text(
        callback.message,
        f"📢 Рассылка для {percent}% пользователей\n\n"
        f"Отправь сообщение (текст, фото или видео):",
        reply_markup=back_button("admin_folder_marketing")
    )


@router.message(AdminStates.waiting_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    percent = data.get('broadcast_percent', 100)
    
    text = message.text or message.caption or ""
    photo_id = message.photo[-1].file_id if message.photo else None
    video_id = message.video.file_id if message.video else None
    
    if not text and not photo_id and not video_id:
        await message.answer("❌ Отправь текст, фото или видео!")
        return
    
    await state.clear()
    
    all_users = await get_all_user_ids()
    
    if percent < 100:
        count = max(1, len(all_users) * percent // 100)
        selected_users = random.sample(all_users, min(count, len(all_users)))
    else:
        selected_users = all_users
    
    await message.answer(f"📢 Начинаю рассылку для {len(selected_users)} пользователей...")
    
    success, failed = await broadcast_message(bot, selected_users, text, photo_id, video_id)
    
    await add_admin_log(message.from_user.username or "Unknown", "broadcast", f"{success} успешно, {failed} не доставлено")
    
    await message.answer(
        f"📢 Рассылка завершена!\n\n"
        f"✅ Успешно: {success}\n"
        f"❌ Не доставлено: {failed}\n"
        f"📊 Всего: {len(selected_users)}",
        reply_markup=admin_main_keyboard()
    )


# =====================================
# 🎟 ВСЕ ПРОМОКОДЫ
# =====================================

@router.callback_query(F.data == "admin_all_promos")
async def admin_all_promos(callback: CallbackQuery):
    if not await can_edit_promos(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promocodes ORDER BY created_at DESC") as cursor:
            promos = await cursor.fetchall()
    
    if not promos:
        await safe_edit_text(callback.message, "🎟 Промокодов пока нет.", reply_markup=back_button("admin_folder_marketing"))
        return
    
    # Inline pagination logic
    await show_promos_page(callback, promos, 0)

async def show_promos_page(callback: CallbackQuery, promos: list, page: int):
    total_pages = (len(promos) + 9) // 10
    start = page * 10
    end = start + 10
    page_promos = promos[start:end]
    
    text = f"🎟 Все промокоды (стр. {page + 1}/{total_pages}):\n\n"
    for promo in page_promos:
        type_names = {"balance": "💰", "ants": "🐜", "color": "🎨"}
        emoji = type_names.get(promo['reward_type'], "🎁")
        text += f"{emoji} {promo['code']}\n"
        text += f"   Награда: {promo['reward_value']}\n"
        text += f"   Осталось: {promo['uses_left']} | Использовано: {promo['total_uses']}\n"
        text += f"   Создал: @{promo['created_by'] or 'Unknown'}\n\n"
    
    buttons = []
    for promo in page_promos:
        buttons.append([InlineKeyboardButton(text=f"🗑 {promo['code']}", callback_data=f"delete_promo_{promo['code']}")])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"promo_page_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"promo_page_{page + 1}"))
    buttons.append(nav)
    
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_marketing")])
    
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("promo_page_"))
async def promo_page(callback: CallbackQuery):
    if not await can_edit_promos(callback.from_user.id):
        return
    
    page = int(callback.data.replace("promo_page_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promocodes ORDER BY created_at DESC") as cursor:
            promos = await cursor.fetchall()
    
    await show_promos_page(callback, promos, page)


@router.callback_query(F.data.startswith("delete_promo_"))
async def delete_promo(callback: CallbackQuery):
    if not await can_edit_promos(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    code = callback.data.replace("delete_promo_", "")
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        await db.commit()
    
    await add_admin_log(callback.from_user.username or "Unknown", "delete_promo", code)
    await callback.answer(f"✅ Промокод {code} удалён!", show_alert=True)
    await admin_all_promos(callback)


# =====================================
# ➕ СОЗДАНИЕ ПРОМОКОДА
# =====================================

@router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_promo_code)
    await safe_edit_text(callback.message, "➕ Создание промокода\n\nВведи название промокода:", reply_markup=back_button("admin_folder_marketing"))


@router.message(AdminStates.waiting_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    code = message.text.strip().upper()
    if not code:
        await message.answer("❌ Введи название промокода!")
        return
    
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.waiting_promo_type)
    await message.answer("Выбери тип награды:", reply_markup=promo_type_keyboard())


@router.callback_query(F.data.startswith("promo_type_"), AdminStates.waiting_promo_type)
async def process_promo_type(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    promo_type = callback.data.replace("promo_type_", "")
    await state.update_data(promo_type=promo_type)
    await state.set_state(AdminStates.waiting_promo_value)
    
    if promo_type == "color":
        await safe_edit_text(callback.message, "Выбери цвет:", reply_markup=colors_keyboard())
    else:
        type_name = "Ежидзиков" if promo_type == "balance" else "муравьёв"
        await safe_edit_text(callback.message, f"Введи количество {type_name}:", reply_markup=back_button("admin_folder_marketing"))


@router.callback_query(F.data.startswith("color_"), AdminStates.waiting_promo_value)
async def process_promo_color(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    color_id = callback.data.replace("color_", "")
    color_name = COLORS.get(color_id, "Не выбран")
    await state.update_data(promo_value=color_name)
    await state.set_state(AdminStates.waiting_promo_uses)
    await safe_edit_text(callback.message, "Введи количество активаций:", reply_markup=back_button("admin_folder_marketing"))


@router.message(AdminStates.waiting_promo_value)
async def process_promo_value(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    try:
        value = int(message.text)
        if value <= 0:
            raise ValueError()
    except:
        await message.answer("❌ Введи положительное число!")
        return
    
    await state.update_data(promo_value=str(value))
    await state.set_state(AdminStates.waiting_promo_uses)
    await message.answer("Введи количество активаций:", reply_markup=back_button("admin_folder_marketing"))


@router.message(AdminStates.waiting_promo_uses)
async def process_promo_uses(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    try:
        uses = int(message.text)
        if uses <= 0:
            raise ValueError()
    except:
        await message.answer("❌ Введи положительное число!")
        return
    
    data = await state.get_data()
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR IGNORE INTO promocodes (code, reward_type, reward_value, uses_left, total_uses, created_by, created_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        ''', (data['promo_code'], data['promo_type'], data['promo_value'], uses, message.from_user.username or "Unknown", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()
    
    await add_admin_log(message.from_user.username or "Unknown", "create_promo", data['promo_code'])
    await state.clear()
    
    type_names = {"balance": "Ежидзики", "ants": "Муравьи", "color": "Цвет"}
    
    # Кнопка для шаринга
    bot_me = await bot.get_me()
    
    await message.answer(
        f"✅ Промокод создан!\n\n"
        f"📝 Код: {data['promo_code']}\n"
        f"🎁 Тип: {type_names.get(data['promo_type'], data['promo_type'])}\n"
        f"💎 Значение: {data['promo_value']}\n"
        f"🔢 Активаций: {uses}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Отослать", switch_inline_query=f"pr {data['promo_code']}")],
            [InlineKeyboardButton(text="В меню", callback_data="admin_folder_marketing")]
        ])
    )


# =====================================
# 💰 УПРАВЛЕНИЕ БАЛАНСОМ И ИГРОКАМИ
# =====================================

@router.callback_query(F.data == "admin_manage_balance")
async def admin_manage_balance(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_user_search)
    await state.update_data(action="balance")
    await safe_edit_text(callback.message, "💰 Поиск игрока\n\nВведи ID, @username или #номер:", reply_markup=back_button("admin_folder_players"))


@router.message(AdminStates.waiting_user_search)
async def process_user_search(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    action = data.get('action', 'balance')
    
    user = await find_user_flexible(message.text.strip())
    
    if not user:
        await message.answer("❌ Пользователь не найден!\n\nВведи ID, @username или #номер:")
        return
    
    # General Logic: Show Actions
    if action == "balance":
        await state.clear() # Clear wait state, set context via keyboard callbacks
        await message.answer(
            f"👤 **Профиль игрока**\n"
            f"ID: `{user['user_id']}`\n"
            f"@{user['username']} ({format_player_number(user['player_number'])})\n"
            f"💰 {user['balance']} Еж.\n"
            f"💎 {user['diamonds']} Алм.\n"
            f"🚫 Ban Ads: {user['ban_ads']}\n"
            f"🚫 Ban Books: {user['ban_books']}",
            reply_markup=player_actions_keyboard(user['user_id']),
            parse_mode="Markdown"
        )
    elif action == "ban":
        await state.update_data(target_user_id=user['user_id'])
        await state.set_state(AdminStates.waiting_ban_reason)
        await message.answer(f"🚫 Бан пользователя: @{user['username']} {format_player_number(user['player_number'])}\n\nВведи причину бана:", reply_markup=back_button("admin_banlist"))
    elif action == "unban":
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?", (user['user_id'],))
            await db.commit()
        await add_admin_log(message.from_user.username or "Unknown", "unban", f"@{user['username']}")
        await state.clear()
        await message.answer(f"✅ Пользователь @{user['username']} разбанен!", reply_markup=admin_main_keyboard())
    elif action == "personal_msg":
        await state.update_data(target_user_id=user['user_id'], target_username=user['username'])
        await state.set_state(AdminStates.waiting_personal_message)
        await message.answer(f"✉️ Написать игроку @{user['username']}\n\nВведи сообщение:", reply_markup=back_button("admin_folder_players"))
    elif action == "view_inventory":
        await state.clear()
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT s.name, i.quantity, i.total_spent, s.currency FROM inventory i
                JOIN shop_items s ON i.item_id = s.id
                WHERE i.user_id = ? AND i.quantity > 0
                ORDER BY s.name
            ''', (user['user_id'],)) as cursor:
                items = await cursor.fetchall()
        if not items:
            await message.answer(f"👾 Инвентарь @{user['username']} пуст!", reply_markup=admin_main_keyboard())
            return
        text = f"👾 Инвентарь @{user['username']}:\n\n"
        total_items = 0
        spent_by_currency = {}
        for item in items:
            text += f"📦 {item['name']} - {item['quantity']} шт. ({item['total_spent']} {CURRENCY_LABELS.get(item['currency'], item['currency'])})\n"
            total_items += item['quantity']
            curr = item['currency']
            spent_by_currency[curr] = spent_by_currency.get(curr, 0) + item['total_spent']
        text += f"\n📊 Всего предметов: {total_items}"
        for curr, spent in spent_by_currency.items():
            text += f"\n💰 Потрачено {CURRENCY_LABELS.get(curr, curr)}: {spent}"
        await message.answer(text, reply_markup=admin_main_keyboard())

# --- PLAYER ACTIONS HANDLERS ---

@router.callback_query(F.data.startswith("act_bal_"))
async def act_balance(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.replace("act_bal_", ""))
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_amount)
    # Отладка — проверить что state реально установился
    check_state = await state.get_state()
    check_data = await state.get_data()
    print(f"[DEBUG] act_balance: set state={check_state}, data={check_data}")
    await callback.answer()
    await callback.message.answer("💰 Введите сумму изменения (+/-):")

@router.callback_query(F.data.startswith("act_ban_"))
async def act_ban(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.replace("act_ban_", ""))
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_ban_reason)
    await callback.answer()
    await callback.message.answer("🚫 Введите причину бана:")

@router.callback_query(F.data.startswith("act_sban_ads_"))
async def act_sban_ads(callback: CallbackQuery):
    user_id = int(callback.data.replace("act_sban_ads_", ""))
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    new_val = 0 if user['ban_ads'] == 1 else 1
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ban_ads = ? WHERE user_id = ?", (new_val, user_id))
        await db.commit()
    await callback.answer(f"Shadow Ban Ads: {new_val}")

@router.callback_query(F.data.startswith("act_sban_books_"))
async def act_sban_books(callback: CallbackQuery):
    user_id = int(callback.data.replace("act_sban_books_", ""))
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    new_val = 0 if user['ban_books'] == 1 else 1
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ban_books = ? WHERE user_id = ?", (new_val, user_id))
        await db.commit()
    await callback.answer(f"Shadow Ban Books: {new_val}")


@router.message(AdminStates.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    print(f"[DEBUG] process_amount called! text={message.text}, from={message.from_user.id}")
    try:
        if not await is_admin(message.from_user.id):
            await message.answer("❌ Нет доступа!")
            await state.clear()
            return
        
        try:
            amount = int(message.text)
        except:
            await message.answer("❌ Введи число!")
            return
        
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        print(f"[DEBUG] state data: {data}, target_user_id={target_user_id}")
        
        if not target_user_id:
            await state.clear()
            await message.answer("❌ Ошибка: потерян ID игрока. Попробуй заново через Поиск.")
            return
        
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_user_id))
            await db.commit()
        
        if amount > 0:
            await add_stat(target_user_id, "balance_add", amount)
        
        await add_admin_log(message.from_user.username or "Unknown", "change_balance", f"user {target_user_id}: {amount}")
        await state.clear()
        
        new_balance = await get_balance(target_user_id)
        await message.answer(
            f"✅ Баланс изменён!\n\n"
            f"Изменение: {'+' if amount > 0 else ''}{amount} Ежидзиков👍\n"
            f"Новый баланс: {new_balance} Ежидзиков👍",
            reply_markup=admin_main_keyboard()
        )
    except Exception as e:
        print(f"[ERROR] process_amount crashed: {e}")
        import traceback
        traceback.print_exc()
        try:
            await message.answer(f"❌ Ошибка: {e}")
        except:
            pass


# =====================================
# 🚫 БАН-ЛИСТ
# =====================================

@router.callback_query(F.data == "admin_banlist")
async def admin_banlist(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await is_admin(callback.from_user.id):
        return
    await safe_edit_text(callback.message, "🚫 Бан-лист", reply_markup=banlist_keyboard())


@router.callback_query(F.data == "admin_ban_user")
async def admin_ban_user(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_user_search)
    await state.update_data(action="ban")
    await safe_edit_text(callback.message, "🚫 Забанить игрока\n\nВведи ID, @username или #номер игрока:", reply_markup=back_button("admin_banlist"))


@router.message(AdminStates.waiting_ban_reason)
async def process_ban_reason(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    reason = message.text.strip() or "Не указана"
    
    if not target_user_id:
        await state.clear()
        await message.answer("❌ Ошибка! Попробуй заново.")
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?", (reason, target_user_id))
        await db.commit()
    
    user = await get_user(target_user_id)
    username = user['username'] if user else "Unknown"
    await add_admin_log(message.from_user.username or "Unknown", "ban", f"@{username}: {reason}")
    await state.clear()
    
    try:
        await bot.send_message(target_user_id, f"🚫 Вы были заблокированы!\n\nПричина: {reason}")
    except:
        pass
    
    await message.answer(f"✅ Пользователь @{username} забанен!\nПричина: {reason}", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin_unban_user")
async def admin_unban_user(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_user_search)
    await state.update_data(action="unban")
    await safe_edit_text(callback.message, "✅ Разбанить игрока\n\nВведи ID, @username или #номер игрока:", reply_markup=back_button("admin_banlist"))


@router.callback_query(F.data == "admin_banned_list")
async def admin_banned_list(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_banned = 1") as cursor:
            banned = await cursor.fetchall()
    
    if not banned:
        await safe_edit_text(callback.message, "📋 Забаненных пользователей нет.", reply_markup=back_button("admin_banlist"))
        return
    
    text = "📋 Забаненные пользователи:\n\n"
    for user in banned[:20]:
        text += f"• @{user['username']} {format_player_number(user['player_number'])}\n  Причина: {user['ban_reason'] or 'Не указана'}\n\n"
    
    await safe_edit_text(callback.message, text, reply_markup=back_button("admin_banlist"))

# =====================================
# 🤡 ФЕЙК АДМИНЫ
# =====================================

@router.callback_query(F.data == "admin_manage_fakes")
async def admin_manage_fakes(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    await safe_edit_text(callback.message, "🤡 Управление Фейковыми Админами", reply_markup=fake_admin_manage_keyboard())

@router.callback_query(F.data == "admin_add_fake")
async def admin_add_fake(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_fake_admin_search)
    await state.update_data(action="add")
    await safe_edit_text(callback.message, "🤡 Введите ID или @username для добавления в Фейки:", reply_markup=back_button("admin_manage_fakes"))

@router.callback_query(F.data == "admin_remove_fake")
async def admin_remove_fake(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.waiting_fake_admin_search)
    await state.update_data(action="remove")
    await safe_edit_text(callback.message, "🤡 Введите ID или @username для удаления из Фейков:", reply_markup=back_button("admin_manage_fakes"))

@router.message(AdminStates.waiting_fake_admin_search)
async def process_fake_admin_action(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id): return
    
    data = await state.get_data()
    action = data.get('action')
    user = await find_user_flexible(message.text.strip())
    
    if not user:
        await message.answer("❌ Игрок не найден.")
        return
        
    new_status = 1 if action == "add" else 0
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_fake_admin = ? WHERE user_id = ?", (new_status, user['user_id']))
        await db.commit()
    
    await state.clear()
    status_text = "назначен Фейком 🤡" if new_status else "убран из Фейков"
    await message.answer(f"✅ Пользователь @{user['username']} {status_text}!", reply_markup=admin_main_keyboard())


# =====================================
# 📋 ДОСЬЕ, ПОДАРОК, СООБЩЕНИЕ
# =====================================

@router.callback_query(F.data == "admin_global_gift")
async def admin_global_gift(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_global_gift)
    await safe_edit_text(callback.message, "🎁 Подарок всем игрокам\n\nВведи количество Ежидзиков👍 для раздачи:", reply_markup=back_button("admin_folder_marketing"))


@router.message(AdminStates.waiting_global_gift)
async def process_global_gift(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError()
    except:
        await message.answer("❌ Введи положительное число!")
        return
    
    await state.clear()
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE is_banned = 0", (amount,))
        await db.commit()
    
    all_users = await get_all_user_ids()
    success = 0
    for uid in all_users:
        try:
            await bot.send_message(uid, f"🎁 Админ прислал вам подарок! 🦔\n\n+{amount} Ежидзиков👍!")
            success += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await add_admin_log(message.from_user.username or "Unknown", "global_gift", f"{amount} Ежидзиков для {len(all_users)} игроков")
    await message.answer(f"🎁 Подарок отправлен!\n\n💰 Сумма: {amount} Ежидзиков👍\n👥 Получили: {len(all_users)} игроков\n📨 Уведомлено: {success}", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin_personal_msg")
async def admin_personal_msg(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_user_search)
    await state.update_data(action="personal_msg")
    await safe_edit_text(callback.message, "✉️ Написать игроку\n\nВведи ID, @username или #номер игрока:", reply_markup=back_button("admin_folder_players"))


@router.message(AdminStates.waiting_personal_message)
async def process_personal_message(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    target_username = data.get('target_username')
    text = message.text or message.caption or ""
    
    if not text:
        await message.answer("❌ Введи текст сообщения!")
        return
    
    await state.clear()
    
    try:
        await bot.send_message(target_user_id, f"✉️ Сообщение от администрации:\n\n{text}")
        await add_admin_log(message.from_user.username or "Unknown", "personal_msg", f"@{target_username}")
        await message.answer(f"✅ Сообщение отправлено @{target_username}!", reply_markup=admin_main_keyboard())
    except:
        await message.answer(f"❌ Не удалось отправить сообщение @{target_username}", reply_markup=admin_main_keyboard())


# =====================================
# 🔧 ТЕХ. РАБОТЫ И НАСТРОЙКИ
# =====================================

@router.callback_query(F.data == "admin_maintenance")
async def admin_maintenance(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    is_on = await check_maintenance()
    await safe_edit_text(
        callback.message,
        f"🔧 Режим технических работ\n\nСтатус: {'🟢 ВКЛЮЧЁН' if is_on else '🔴 ВЫКЛЮЧЕН'}\n\nКогда включён — обычные пользователи не могут пользоваться ботом.",
        reply_markup=maintenance_keyboard(is_on)
    )


@router.callback_query(F.data == "toggle_maintenance")
async def toggle_maintenance(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    is_on = await check_maintenance()
    new_value = "0" if is_on else "1"
    await set_setting("maintenance_mode", new_value)
    await add_admin_log(callback.from_user.username or "Unknown", "maintenance", f"{'ON' if new_value == '1' else 'OFF'}")
    is_on_now = new_value == "1"
    await safe_edit_text(
        callback.message,
        f"🔧 Режим технических работ\n\nСтатус: {'🟢 ВКЛЮЧЁН' if is_on_now else '🔴 ВЫКЛЮЧЕН'}\n\nКогда включён — обычные пользователи не могут пользоваться ботом.",
        reply_markup=maintenance_keyboard(is_on_now)
    )
    await callback.answer(f"✅ Тех. работы {'включены' if is_on_now else 'выключены'}!", show_alert=True)


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    feed_cost = await get_setting("feed_cost", "150")
    ant_cost = await get_setting("ant_catch_cost", "200")
    ant_income = await get_setting("ant_income", "10")
    daily = await get_setting("daily_bonus", "25")
    await safe_edit_text(
        callback.message,
        f"⚙️ Настройки бота\n\n🥕 Цена кормления: {feed_cost} Ежидзиков👍\n🐜 Цена ловли муравья: {ant_cost} Ежидзиков👍\n💰 Доход муравья/час: {ant_income} Ежидзиков👍\n🎁 Ежедневный бонус: {daily} Ежидзиков👍\n\nНажми чтобы изменить:",
        reply_markup=settings_keyboard()
    )


@router.callback_query(F.data.startswith("setting_"))
async def setting_change(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    setting_key = callback.data.replace("setting_", "")
    setting_names = {"feed_cost": "🥕 Цена кормления", "ant_catch_cost": "🐜 Цена ловли муравья", "ant_income": "💰 Доход муравья/час", "daily_bonus": "🎁 Ежедневный бонус"}
    await state.update_data(setting_key=setting_key)
    await state.set_state(AdminStates.waiting_setting_value)
    current = await get_setting(setting_key, "0")
    await safe_edit_text(callback.message, f"⚙️ {setting_names.get(setting_key, setting_key)}\n\nТекущее значение: {current}\n\nВведи новое значение:", reply_markup=back_button("admin_folder_settings"))


@router.message(AdminStates.waiting_setting_value)
async def process_setting_value(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    try:
        value = int(message.text)
        if value < 0:
            raise ValueError()
    except:
        await message.answer("❌ Введи неотрицательное число!")
        return
    data = await state.get_data()
    setting_key = data.get('setting_key')
    await set_setting(setting_key, str(value))
    await add_admin_log(message.from_user.username or "Unknown", "change_setting", f"{setting_key} = {value}")
    await state.clear()
    await message.answer(f"✅ Настройка изменена!\n\n{setting_key} = {value}", reply_markup=admin_main_keyboard())

@router.callback_query(F.data == "admin_download_db")
async def admin_download_db(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    
    file = FSInputFile(DB_NAME)
    await callback.message.answer_document(file, caption="📥 База данных")

# =====================================
# 📜 ЛОГИ И УПРАВЛЕНИЕ АДМИНАМИ
# =====================================

@router.callback_query(F.data == "admin_logs")
async def admin_logs(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        await callback.answer("❌ Только главный админ!", show_alert=True)
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 20") as cursor:
            logs = await cursor.fetchall()
    if not logs:
        await safe_edit_text(callback.message, "📜 Логов пока нет.", reply_markup=back_button("admin_panel"))
        return
    text = "📜 Последние действия админов:\n\n"
    for log in logs:
        text += f"👤 @{log['admin_username']}\n   {log['action']}: {log['target_info']}\n   🕐 {log['timestamp']}\n\n"
    await safe_edit_text(callback.message, text, reply_markup=back_button("admin_panel"))


@router.callback_query(F.data == "admin_manage_admins")
async def admin_manage_admins(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        await callback.answer("❌ Только главный админ может управлять админами!", show_alert=True)
        return
    await safe_edit_text(callback.message, "👑 Управление админами", reply_markup=admin_manage_admins_keyboard())


@router.callback_query(F.data == "admin_list_admins")
async def admin_list_admins(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    admins = await get_all_admins()
    text = "👑 Список админов:\n\n"
    for admin in admins:
        is_main_mark = " 👑 ГЛАВНЫЙ" if admin['username'] == MAIN_ADMIN_USERNAME else ""
        can_promo = " (+промо)" if admin['can_edit_promos'] else ""
        text += f"• @{admin['username']} (ID: {admin['user_id'] or '?'}){is_main_mark}{can_promo}\n"
    await safe_edit_text(callback.message, text, reply_markup=back_button("admin_manage_admins"))


@router.callback_query(F.data == "admin_add_admin")
async def admin_add_admin(callback: CallbackQuery, state: FSMContext):
    if not await is_main_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_admin_username)
    await safe_edit_text(callback.message, "➕ Введи @username нового админа (без @):\n\n⚠️ Пользователь должен хотя бы раз написать боту!", reply_markup=back_button("admin_manage_admins"))


@router.message(AdminStates.waiting_admin_username)
async def process_admin_username(message: Message, state: FSMContext):
    if not await is_main_admin(message.from_user.id):
        return
    username = message.text.replace("@", "").strip()
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
            user = await cursor.fetchone()
    if not user:
        await state.clear()
        await message.answer(f"❌ Пользователь @{username} не найден!\n\nОн должен хотя бы раз написать боту.", reply_markup=admin_main_keyboard())
        return
    await add_admin(username, message.from_user.username or "Unknown")
    await add_admin_log(message.from_user.username or "Unknown", "add_admin", f"@{username}")
    await state.clear()
    await message.answer(f"✅ Админ @{username} добавлен!", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin_remove_admin")
async def admin_remove_admin(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    admins = await get_all_admins()
    buttons = []
    for admin in admins:
        if admin['username'] != MAIN_ADMIN_USERNAME:
            buttons.append([InlineKeyboardButton(text=f"❌ @{admin['username']}", callback_data=f"remove_admin_{admin['username']}")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_manage_admins")])
    if len(buttons) == 1:
        await callback.answer("Нет админов для удаления!", show_alert=True)
        return
    await safe_edit_text(callback.message, "➖ Выбери админа для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("remove_admin_"))
async def confirm_remove_admin(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    username = callback.data.replace("remove_admin_", "")
    if await remove_admin(username):
        await add_admin_log(callback.from_user.username or "Unknown", "remove_admin", f"@{username}")
        await callback.answer(f"✅ Админ @{username} удалён!", show_alert=True)
    else:
        await callback.answer("❌ Нельзя удалить главного админа!", show_alert=True)
    await callback.message.edit_text("👑 Управление админами", reply_markup=admin_manage_admins_keyboard())


# =====================================
# 🛒 ТОВЫРЫ (АДМИН)
# =====================================

@router.callback_query(F.data == "admin_shop")
async def admin_shop_menu(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    await safe_edit_text(callback.message, "🛒 Товыры - управление магазином", reply_markup=admin_shop_keyboard())


@router.callback_query(F.data == "admin_add_item")
async def admin_add_item(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_item_name)
    await safe_edit_text(callback.message, "➕ Введи название нового товара:", reply_markup=back_button("admin_shop"))


@router.message(AdminStates.waiting_item_name)
async def process_item_name(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    item_name = message.text.strip()
    if not item_name:
        await message.answer("❌ Введи название товара!")
        return
    await state.update_data(item_name=item_name)
    await state.set_state(AdminStates.waiting_item_price)
    await message.answer(f"💰 Введи цену для товара «{item_name}»:", reply_markup=back_button("admin_shop"))


@router.message(AdminStates.waiting_item_price)
async def process_item_price(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    try:
        price = int(message.text)
        if price < 0:
            raise ValueError()
    except:
        await message.answer("❌ Введи неотрицательное число!")
        return
    
    await state.update_data(item_price=price)
    await state.set_state(AdminStates.waiting_item_currency)
    await message.answer(f"💱 Выбери валюту для товара:", reply_markup=shop_currency_keyboard())

@router.callback_query(F.data.startswith("shop_curr_"), AdminStates.waiting_item_currency)
async def process_item_currency(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    currency_code = callback.data.replace("shop_curr_", "")
    # Валюты: balance (ежидзики), skin (кожа), diamonds (алмазы)
    currency = currency_code 
    
    data = await state.get_data()
    item_name = data['item_name']
    item_price = data['item_price']
    
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute("INSERT INTO shop_items (name, price, currency) VALUES (?, ?, ?)", (item_name, item_price, currency))
            await db.commit()
            await add_admin_log(callback.from_user.username or "Unknown", "add_item", f"{item_name}: {item_price} {currency}")
            await state.clear()
            
            currency_names = {"balance": "Ежидзиков", "skin": "Кожи слона", "diamonds": "Алмазов"}
            curr_name = currency_names.get(currency, currency)
            price_text = f"{item_price} {curr_name}" if item_price > 0 else "Бесплатно!"
            
            await callback.message.answer(f"✅ Товар добавлен!\n\n📦 {item_name}\n💰 {price_text}", reply_markup=admin_main_keyboard())
        except:
            await state.clear()
            await callback.message.answer("❌ Товар с таким названием уже существует!", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin_delete_item")
async def admin_delete_item(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM shop_items ORDER BY price ASC") as cursor:
            items = await cursor.fetchall()
    if not items:
        await callback.answer("📭 Магазин пуст!", show_alert=True)
        return
    buttons = []
    for item in items[:15]:
        buttons.append([InlineKeyboardButton(text=f"🗑 {item['name']} ({item['price']})", callback_data=f"del_item_{item['id']}")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_shop")])
    await safe_edit_text(callback.message, "🗑 Выбери товар для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("del_item_"))
async def delete_item(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    item_id = int(callback.data.replace("del_item_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name FROM shop_items WHERE id = ?", (item_id,)) as cursor:
            item = await cursor.fetchone()
        if item:
            await db.execute("DELETE FROM shop_items WHERE id = ?", (item_id,))
            await db.execute("DELETE FROM inventory WHERE item_id = ?", (item_id,))
            await db.commit()
            await add_admin_log(callback.from_user.username or "Unknown", "delete_item", item[0])
            await callback.answer(f"✅ Товар «{item[0]}» удалён!", show_alert=True)
    await admin_delete_item(callback)


@router.callback_query(F.data == "admin_view_inventory")
async def admin_view_inventory(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_user_search)
    await state.update_data(action="view_inventory")
    await safe_edit_text(callback.message, "👀 Введи ID, @username или #номер игрока:", reply_markup=back_button("admin_folder_content"))


# =====================================
# 🖼 МОДЕРАЦИЯ РЕКЛАМЫ
# =====================================

@router.callback_query(F.data == "admin_moderate_ads")
async def admin_moderate_ads(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ads WHERE status = 'pending' LIMIT 1") as cursor:
            ad = await cursor.fetchone()
    if not ad:
        await callback.answer("✅ Нет рекламы на модерации!", show_alert=True)
        return
    await safe_delete(callback.message)
    await callback.message.answer_photo(ad['file_id'], caption=f"🖼 Реклама на модерацию\n\nID: {ad['id']}\nОт: {ad['user_id']}", reply_markup=ad_moderation_keyboard(ad['id']))


@router.callback_query(F.data.startswith("approve_ad_"))
async def approve_ad(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    ad_id = int(callback.data.replace("approve_ad_", ""))
    
    # Race Condition Protection
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT status, user_id FROM ads WHERE id = ?", (ad_id,)) as cursor:
            ad = await cursor.fetchone()
        
        if not ad or ad['status'] != 'pending':
            await callback.answer("✋ Заявка уже обработана другим администратором!", show_alert=True)
            await safe_delete(callback.message)
            await admin_moderate_ads(callback)
            return

        await db.execute("UPDATE ads SET status = 'approved' WHERE id = ?", (ad_id,))
        await db.commit()
        
    if ad:
        try:
            await bot.send_message(ad['user_id'], "✅ Ваша реклама одобрена и добавлена в ротацию!")
        except:
            pass
            
    await add_admin_log(callback.from_user.username or "Unknown", "approve_ad", str(ad_id))
    await callback.answer("✅ Реклама одобрена!", show_alert=True)
    await safe_delete(callback.message)
    # Load next
    await admin_moderate_ads(callback)


@router.callback_query(F.data.startswith("reject_ad_"))
async def reject_ad(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    ad_id = int(callback.data.replace("reject_ad_", ""))
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT status, user_id FROM ads WHERE id = ?", (ad_id,)) as cursor:
            ad = await cursor.fetchone()
            
        if not ad or ad['status'] != 'pending':
            await callback.answer("✋ Заявка уже обработана другим администратором!", show_alert=True)
            await safe_delete(callback.message)
            await admin_moderate_ads(callback)
            return

        await db.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        await db.commit()
        
    if ad:
        await update_balance(ad['user_id'], 70)
        try:
            await bot.send_message(ad['user_id'], "❌ Ваша реклама отклонена.\n💰 70 Ежидзиков👍 возвращены на баланс.")
        except:
            pass
            
    await add_admin_log(callback.from_user.username or "Unknown", "reject_ad", str(ad_id))
    await callback.answer("❌ Реклама отклонена!", show_alert=True)
    await safe_delete(callback.message)
    await admin_moderate_ads(callback)


@router.callback_query(F.data == "admin_delete_ads")
async def admin_delete_ads(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ads WHERE status = 'approved'") as cursor:
            ads = await cursor.fetchall()
    if not ads:
        await callback.answer("📭 Нет одобренной рекламы!", show_alert=True)
        return
    buttons = []
    for ad in ads[:10]:
        buttons.append([InlineKeyboardButton(text=f"👁 Реклама #{ad['id']}", callback_data=f"preview_ad_{ad['id']}")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_marketing")])
    await safe_edit_text(callback.message, f"🗑 Удаление рекламы\n\nВсего одобренных: {len(ads)}\n\nНажми для предпросмотра:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("preview_ad_"))
async def preview_ad(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    ad_id = int(callback.data.replace("preview_ad_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ads WHERE id = ?", (ad_id,)) as cursor:
            ad = await cursor.fetchone()
    if not ad:
        await callback.answer("❌ Реклама не найдена!", show_alert=True)
        return
    await safe_delete(callback.message)
    await callback.message.answer_photo(
        ad['file_id'], 
        caption=f"🖼 Предпросмотр рекламы #{ad['id']}\n\nОт: {ad['user_id']}", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_ad_{ad_id}")], 
            [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_delete_ads")]
        ])
    )


@router.callback_query(F.data.startswith("del_ad_"))
async def delete_ad(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    ad_id = int(callback.data.replace("del_ad_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        await db.commit()
    await add_admin_log(callback.from_user.username or "Unknown", "delete_ad", str(ad_id))
    await callback.answer("✅ Реклама удалена!", show_alert=True)
    await safe_delete(callback.message)
    await admin_delete_ads(callback)

# =====================================
# 🖼 УПРАВЛЕНИЕ МЕДИА (/add)
# =====================================

@router.callback_query(F.data == "admin_manage_media")
async def admin_manage_media(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        await callback.answer("❌ Только главный админ!", show_alert=True)
        return
    
    text = (
        "🖼 **Управление медиа экранов**\n\n"
        "Вы можете прикрепить фото или видео к основным экранам бота.\n"
        "Чтобы добавить/изменить медиа, отправьте мне картинку с подписью:\n"
        "`/add <имя_экрана>`\n\n"
        "**Доступные имена экранов:**\n"
        "`menu`, `casino`, `shop`, `pet`, `feed`, `bonuses`, `transfer`, `exchange`, `website`, `call`, `support`"
    )
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT screen_name FROM screen_media") as cursor:
            medias = await cursor.fetchall()
    
    buttons = []
    if medias:
        for m in medias:
             buttons.append([InlineKeyboardButton(text=f"🗑 Удалить: {m['screen_name']}", callback_data=f"del_media_{m['screen_name']}")])
    
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_content")])
    
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

@router.message(Command("add"))
async def cmd_add_media(message: Message, command: CommandObject):
    if not await is_main_admin(message.from_user.id):
        return

    screen_name = command.args
    if not screen_name:
        await message.answer("❌ Укажите имя экрана! Пример: `/add menu`")
        return
    
    file_id = None
    media_type = None
    
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    else:
        await message.answer("❌ Прикрепите фото или видео к команде!")
        return

    await set_screen_media(screen_name.lower(), file_id, media_type)
    await message.answer(f"✅ Медиа для экрана `{screen_name}` установлено!")

@router.callback_query(F.data.startswith("del_media_"))
async def delete_media_entry(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    
    screen_name = callback.data.replace("del_media_", "")
    await delete_screen_media(screen_name)
    await callback.answer(f"✅ Медиа для {screen_name} удалено!")
    await admin_manage_media(callback)


# =====================================
# 📝 КАСТОМНЫЕ КОМАНДЫ
# =====================================

@router.callback_query(F.data == "admin_add_command")
async def admin_add_command(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_command_name)
    await safe_edit_text(callback.message, "📝 Введи команду (например: /hi, /photos, /info):", reply_markup=back_button("admin_folder_content"))


@router.message(AdminStates.waiting_command_name)
async def process_command_name(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    command = message.text.strip()
    if not command.startswith("/"):
        command = "/" + command
    await state.update_data(command_name=command)
    await state.set_state(AdminStates.waiting_command_response)
    await message.answer(f"📝 Теперь отправь ответ для команды {command}\n\nМожно отправить текст, фото или видео с подписью.", reply_markup=back_button("admin_folder_content"))


@router.message(AdminStates.waiting_command_response)
async def process_command_response(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    command_name = data.get('command_name')
    response_text = message.text or message.caption or ""
    media_type = None
    media_file_id = None
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    if not response_text and not media_file_id:
        await message.answer("❌ Отправь текст, фото или видео!")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute('INSERT INTO custom_commands (command, response_text, media_type, media_file_id, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)', (command_name, response_text, media_type, media_file_id, message.from_user.username or "Unknown", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            await db.commit()
            await add_admin_log(message.from_user.username or "Unknown", "add_command", command_name)
            await state.clear()
            await message.answer(f"✅ Команда {command_name} создана!", reply_markup=admin_main_keyboard())
        except:
            await state.clear()
            await message.answer(f"❌ Команда {command_name} уже существует!", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin_manage_commands")
async def admin_manage_commands(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM custom_commands ORDER BY command") as cursor:
            commands = await cursor.fetchall()
    if not commands:
        await safe_edit_text(callback.message, "📋 Нет созданных команд", reply_markup=back_button("admin_folder_content"))
        return
    buttons = []
    for cmd in commands:
        buttons.append([InlineKeyboardButton(text=f"🗑 {cmd['command']}", callback_data=f"delete_cmd_{cmd['id']}")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="admin_folder_content")])
    await safe_edit_text(callback.message, f"📋 Управление командами ({len(commands)} шт.)\n\nНажми чтобы удалить:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("delete_cmd_"))
async def delete_command(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    cmd_id = int(callback.data.replace("delete_cmd_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT command FROM custom_commands WHERE id = ?", (cmd_id,)) as cursor:
            cmd = await cursor.fetchone()
        if cmd:
            await db.execute("DELETE FROM custom_commands WHERE id = ?", (cmd_id,))
            await db.commit()
            await add_admin_log(callback.from_user.username or "Unknown", "delete_command", cmd[0])
    await callback.answer("✅ Команда удалена!", show_alert=True)
    await admin_manage_commands(callback)


# =====================================
# 📚 МОДЕРАЦИЯ КНИГ (v3.8)
# =====================================

@router.callback_query(F.data.startswith("approve_book_"))
async def approve_book(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    
    book_id = int(callback.data.replace("approve_book_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Check race condition
        async with db.execute("SELECT status, author_id, title FROM books WHERE id = ?", (book_id,)) as cursor:
            book = await cursor.fetchone()
            
        if not book or book['status'] != 'pending':
            await callback.answer("✋ Заявка уже обработана другим админом!", show_alert=True)
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n⚠️ ОБРАБОТАНО")
            return
        
        await db.execute("UPDATE books SET status = 'approved' WHERE id = ?", (book_id,))
        await db.commit()
    
    if book:
        try:
            await bot.send_message(book['author_id'], f"✅ Ваша книга «{book['title']}» одобрена и добавлена в магазин!")
        except: pass

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ ОДОБРЕНО")
    await callback.answer("Книга одобрена!")

@router.callback_query(F.data.startswith("reject_book_"))
async def reject_book(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id): return
    
    book_id = int(callback.data.replace("reject_book_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Check race condition
        async with db.execute("SELECT status, author_id, title FROM books WHERE id = ?", (book_id,)) as cursor:
            book = await cursor.fetchone()
            
        if not book or book['status'] != 'pending':
            await callback.answer("✋ Заявка уже обработана другим админом!", show_alert=True)
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n⚠️ ОБРАБОТАНО")
            return
            
        await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        await db.commit()
    
    if book:
        try:
            await bot.send_message(book['author_id'], f"❌ Ваша книга «{book['title']}» была отклонена администратором.")
        except: pass

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ ОТКЛОНЕНО")
    await callback.answer("Книга отклонена!")


# =====================================
# 💬 ОТВЕТ НА ТИКЕТЫ
# =====================================

@router.callback_query(F.data.startswith("reply_ticket_"))
async def reply_ticket(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    ticket_id = int(callback.data.replace("reply_ticket_", ""))
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AdminStates.waiting_support_reply)
    await callback.message.answer("💬 Напиши ответ пользователю:\n\nМожешь прикрепить фото или видео.", reply_markup=back_button("admin_panel"))


@router.message(AdminStates.waiting_support_reply)
async def process_support_reply(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    data = await state.get_data()
    ticket_id = data.get('ticket_id')
    reply_text = message.text or message.caption or ""
    if not reply_text and not message.photo and not message.video:
        await message.answer("❌ Отправь текст, фото или видео!")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)) as cursor:
            ticket = await cursor.fetchone()
        if ticket:
            await db.execute("UPDATE support_tickets SET status = 'answered' WHERE id = ?", (ticket_id,))
            await db.commit()
            user_id = ticket['user_id']
            ticket_type = ticket['ticket_type']
            prefix = "🆘 Ответ от техподдержки:\n\n" if ticket_type == "support" else "💫 Ответ на ваше предложение:\n\n"
            try:
                if message.photo:
                    await bot.send_photo(user_id, message.photo[-1].file_id, caption=prefix + reply_text)
                elif message.video:
                    await bot.send_video(user_id, message.video.file_id, caption=prefix + reply_text)
                else:
                    await bot.send_message(user_id, prefix + reply_text)
            except:
                pass
    await state.clear()
    await message.answer("✅ Ответ отправлен пользователю!", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("ignore_ticket_"))
async def ignore_ticket(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    ticket_id = int(callback.data.replace("ignore_ticket_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)) as cursor:
            ticket = await cursor.fetchone()
        if ticket:
            await db.execute("UPDATE support_tickets SET status = 'ignored' WHERE id = ?", (ticket_id,))
            await db.commit()
            user_id = ticket['user_id']
            ticket_type = ticket['ticket_type']
            msg = "😔 Админ не ответил на вопрос в техподдержку." if ticket_type == "support" else "😔 Админ не ответил на ваше предложение обновления."
            try:
                await bot.send_message(user_id, msg)
            except:
                pass
    await callback.answer("🚫 Тикет проигнорирован", show_alert=True)
    await safe_delete(callback.message)


# =====================================
# 🎟 ПРОМОКОДЫ И КАСТОМНЫЕ КОМАНДЫ (ВВОД)
# =====================================

@router.message(F.text)
async def check_promocode_and_commands(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    text = message.text.strip()
    if not text:
        return
    is_banned, _ = await check_user_banned(user_id)
    if is_banned:
        return
    await update_username(user_id, username)
    
    # Custom commands
    if text.startswith("/"):
        command = text.split()[0].lower()
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM custom_commands WHERE LOWER(command) = ?", (command,)) as cursor:
                cmd = await cursor.fetchone()
            if cmd:
                try:
                    if cmd['media_type'] == "photo" and cmd['media_file_id']:
                        await message.answer_photo(cmd['media_file_id'], caption=cmd['response_text'] or None)
                    elif cmd['media_type'] == "video" and cmd['media_file_id']:
                        await message.answer_video(cmd['media_file_id'], caption=cmd['response_text'] or None)
                    elif cmd['response_text']:
                        await message.answer(cmd['response_text'])
                except:
                    pass
                return

    # Promocodes
    await process_promocode(message, user_id, text.upper())

async def process_promocode(message: Message, user_id: int, code: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM used_promocodes WHERE user_id = ? AND code = ?", (user_id, code)) as cursor:
            if await cursor.fetchone():
                await message.answer("❌ Вы уже активировали этот промокод!")
                return
        async with db.execute("SELECT * FROM promocodes WHERE code = ? AND uses_left > 0", (code,)) as cursor:
            promo = await cursor.fetchone()
        if not promo:
            # Не отвечаем, если это просто текст
            return
        
        reward_type = promo['reward_type']
        reward_value = promo['reward_value']
        
        if reward_type == "balance":
            await update_balance(user_id, int(reward_value))
            reward_text = f"+{reward_value} Ежидзиков👍"
        elif reward_type == "ants":
            await db.execute("UPDATE users SET ants = ants + ? WHERE user_id = ?", (int(reward_value), user_id))
            reward_text = f"+{reward_value} муравьёв 🐜"
        elif reward_type == "color":
            await db.execute("UPDATE users SET hedgehog_color = ? WHERE user_id = ?", (reward_value, user_id))
            reward_text = f"Новый цвет: {reward_value}"
        else:
            reward_text = "Награда получена!"
            
        await db.execute("INSERT INTO used_promocodes (user_id, code, used_at) VALUES (?, ?, ?)", (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1, total_uses = total_uses + 1 WHERE code = ?", (code,))
        await db.commit()
    
    is_user_admin = await is_admin(user_id)
    await message.answer(f"🎉 Промокод активирован!\n\n{reward_text}", reply_markup=main_menu_keyboard(is_user_admin))

# =====================================
# 🎟 INLINE QUERY
# =====================================

@router.inline_query()
async def inline_query_handler(query: InlineQuery):
    text = query.query.strip()
    
    # Режим "pr CODE"
    if text.startswith("pr "):
        code = text[3:].strip().upper()
        if not code:
            return
            
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM promocodes WHERE code = ? AND uses_left > 0", (code,)) as cursor:
                promo = await cursor.fetchone()
        
        if promo:
            type_names = {"balance": "ежидзиков👍", "ants": "муравьев🐜", "color": "цветов🎨"}
            curr_name = type_names.get(promo['reward_type'], promo['reward_type'])
            
            # Deep linking parameter for start
            deep_link = f"promo_{code}"
            bot_username = (await bot.get_me()).username
            url = f"https://t.me/{bot_username}?start={deep_link}"
            
            description_text = (
                f"🦔 Промокод в боте Говорящий Еж! 🦔\n"
                f"⚡ Активаций осталось на момент сообщения: {promo['uses_left']}\n"
                f"🌟 Дает: {promo['reward_value']} {curr_name}"
            )
            
            result = InlineQueryResultArticle(
                id=f"promo_{code}",
                title="👍 Нажми СЮДА!",
                description=f"Промокод: {code}",
                input_message_content=InputTextMessageContent(message_text=description_text),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔥 Забрать", url=url)]
                ])
            )
            
            await query.answer([result], cache_time=1)
    
    # Если пустой запрос или только имя бота
    elif text == "":
        result = InlineQueryResultArticle(
            id="info",
            title="Прочитайте подробнее в инфо",
            description="Напишите 'pr КОД' для отправки промокода",
            input_message_content=InputTextMessageContent(message_text="Используйте inline режим для отправки промокодов!"),
        )
        await query.answer([result], cache_time=300)

# =====================================
# ⏰ ФОНОВЫЕ ЗАДАЧИ
# =====================================

async def ant_income_loop():
    while True:
        try:
            ant_income = int(await get_setting("ant_income", "10"))
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT user_id, ants FROM users WHERE ants > 0 AND status = 'alive'") as cursor:
                    users = await cursor.fetchall()
                count = 0
                for user_id, ants in users:
                    income = ants * ant_income
                    await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (income, user_id))
                    count += 1
                await db.commit()
        except Exception as e:
            print(f"Ошибка начисления муравьёв: {e}")
        await asyncio.sleep(3600)

async def hunger_loop():
    # Реализация механики выживания v3.8
    # Еж умирает за 3 дня (72 часа) = 100% сытости.
    # Обновление каждые 10 минут.
    # 72 часа = 432 интервала по 10 минут.
    # Потеря сытости за интервал = 100 / 432 ≈ 0.2315%
    
    base_hunger_drop = 0.2315
    furniture_hunger_drop = 0.15 # Сниженная скорость с мебелью
    
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                # Получаем всех живых пользователей
                async with db.execute("SELECT user_id, satiety, alert_sent FROM users WHERE status = 'alive'") as cursor:
                    users = await cursor.fetchall()
                
                for user in users:
                    uid = user['user_id']
                    current_satiety = user['satiety']
                    
                    # Проверяем наличие мебели
                    has_furniture = False
                    async with db.execute('''
                        SELECT i.quantity, s.name FROM inventory i
                        JOIN shop_items s ON i.item_id = s.id
                        WHERE i.user_id = ? AND i.quantity > 0
                    ''', (uid,)) as inv_cursor:
                        items = await inv_cursor.fetchall()
                        for item in items:
                            for kw in FURNITURE_KEYWORDS:
                                if kw in item['name'].lower():
                                    has_furniture = True
                                    break
                            if has_furniture: break
                    
                    drop_rate = furniture_hunger_drop if has_furniture else base_hunger_drop
                    new_satiety = current_satiety - drop_rate
                    
                    # Alert logic (20%)
                    need_alert = False
                    if new_satiety <= 20.0 and user['alert_sent'] == 0:
                        try:
                            await bot.send_message(uid, "🆘 ХОЗЯИН! Я ГОЛОДЕН! Моя сытость упала до 20%!\nСрочно покорми меня, иначе я умру!")
                            need_alert = True
                        except: pass
                    
                    # Death logic
                    if new_satiety <= 0:
                        await db.execute("UPDATE users SET status = 'dead', satiety = 0 WHERE user_id = ?", (uid,))
                        try:
                            await bot.send_message(uid, "☠️ Ваш ёжик умер от голода...\nНажмите /start или любую кнопку для перехода в посмертие.", reply_markup=death_reply_keyboard())
                        except: pass
                    else:
                        if need_alert:
                            await db.execute("UPDATE users SET satiety = ?, alert_sent = 1 WHERE user_id = ?", (new_satiety, uid))
                        else:
                            await db.execute("UPDATE users SET satiety = ? WHERE user_id = ?", (new_satiety, uid))
                        
                await db.commit()
                    
        except Exception as e:
            print(f"Ошибка цикла голода: {e}")
        await asyncio.sleep(600) # Every 10 minutes

# =====================================
# 🚀 ЗАПУСК БОТА
# =====================================
async def main():
    try:
        print("🚀 Запуск бота...")
        await init_db()
        print("✅ База данных инициализирована")
        
        # Start background tasks
        asyncio.create_task(ant_income_loop())
        asyncio.create_task(hunger_loop())
        
        print("=" * 50)
        print("🦔 Бот 'Говорящий Еж' v3.8 (Survival Update) запущен!")
        print("=" * 50)
        print(f"👑 Главный админ: @{MAIN_ADMIN_USERNAME}")
        print(f"📢 Канал: {CHANNEL_LINK}")
        print("=" * 50)
        
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ ФАТАЛЬНАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
