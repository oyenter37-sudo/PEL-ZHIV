#!/usr/bin/env python3
"""
💣 Мины Бот (@gminesdedbot) — Клон gminesbot
Казино-бот с игрой Мины, рулеткой, костями, монеткой.
Запускается параллельно с основным ботом из Bot.py
"""

import asyncio
import sqlite3
import random
import math
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gmines")

# ═══════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════

BOT_TOKEN = "8923946450:AAFnkauyQv3fNtEO6o5amECF0xb0bEDJ4-E"
OWNER_IDS = [8440455988, 8771403623]
DB_PATH = "gmines_bot.db"

CURRENCY_NAME = "монеты"
CURRENCY_EMOJI = "💎"
BOT_NAME = "Мины Бот"

# Настройки Mines
MINES_GRID_SIZE = 25  # 5x5
MINES_MIN_BET = 10
MINES_MAX_BET = 1000000
MINES_BOMB_OPTIONS = [1, 3, 5, 10, 15, 20, 24]

# Настройки рулетки
ROULETTE_COLORS = ["🔴", "⚫", "🟢"]
ROULETTE_NUMBERS_RED = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
ROULETTE_NUMBERS_BLACK = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]

# Настройки костей
DICE_MIN_BET = 10
DICE_TARGET_RANGE = (2, 98)

# Ежедневный бонус
DAILY_BASE = 500
DAILY_STREAK_BONUS = 50  # за каждый день подряд
DAILY_MAX_STREAK = 30

# Реферал
REF_BONUS = 300  # бонус приглашённому
REF_REWARD = 100  # бонус пригласившему (за каждый тап друга)
REF_PERCENT = 0.05  # 5% от ставок друга

# Магазин
SHOP_ITEMS = {
    "lucky_charm": {"name": "🍀 Амулет удачи", "desc": "+5% к множителю в Минах", "price": 5000, "duration_days": 7},
    "shield": {"name": "🛡️ Щит", "desc": "1 бесплатная страховка от мины в день", "price": 10000, "duration_days": 7},
    "x2_daily": {"name": "✨ Двойной бонус", "desc": "x2 к ежедневному бонусу", "price": 8000, "duration_days": 7},
    "vip_pass": {"name": "👑 VIP пропуск", "desc": "Ставки от 1 монеты + приоритет", "price": 25000, "duration_days": 30},
    "magnet": {"name": "🧲 Магнит", "desc": "+3% к шансу выигрыша в рулетке", "price": 7000, "duration_days": 7},
    "golden_dice": {"name": "🎲 Золотые кости", "desc": "+5% к шансу выигрыша в костях", "price": 6000, "duration_days": 7},
}

# ═══════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                total_lost INTEGER DEFAULT 0,
                total_bets INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                mines_played INTEGER DEFAULT 0,
                roulette_played INTEGER DEFAULT 0,
                dice_played INTEGER DEFAULT 0,
                coinflip_played INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT DEFAULT NULL,
                referrer_id INTEGER DEFAULT NULL,
                referrals_count INTEGER DEFAULT 0,
                referrals_earned INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT DEFAULT NULL,
                join_date TEXT,
                last_active TEXT
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS active_mines (
                user_id INTEGER PRIMARY KEY,
                bet INTEGER,
                bombs INTEGER,
                revealed TEXT DEFAULT '',
                field TEXT,
                multiplier REAL DEFAULT 1.0,
                started_at TEXT
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_key TEXT,
                expires_at TEXT,
                purchased_at TEXT
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                description TEXT,
                timestamp TEXT
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                reward INTEGER,
                uses_left INTEGER,
                total_uses INTEGER DEFAULT 0,
                created_by TEXT,
                created_at TEXT
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS used_promos (
                user_id INTEGER,
                code TEXT,
                used_at TEXT,
                PRIMARY KEY(user_id, code)
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS broadcast_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                sent_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')

        # Default settings
        db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('maintenance', '0')")
        db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('min_bet', '10')")
        db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('max_bet', '1000000')")
        db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('welcome_bonus', '1000')")

    logger.info("База данных Мины Бот инициализирована")


# ═══════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════

def get_user(user_id: int):
    with get_db() as db:
        cur = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone()


def create_user(user_id: int, username: str, referrer_id: int = None):
    welcome = int(get_setting("welcome_bonus", "1000"))
    balance = welcome if referrer_id is None else welcome + REF_BONUS
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as db:
        db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, balance, referrer_id, join_date, last_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, balance, referrer_id, now, now))

        if referrer_id:
            db.execute('''
                UPDATE users SET referrals_count = referrals_count + 1,
                                 referrals_earned = referrals_earned + REF_REWARD
                WHERE user_id = ?
            ''', (referrer_id,))
            db.execute('''
                UPDATE users SET balance = balance + REF_REWARD WHERE user_id = ?
            ''', (referrer_id,))
            add_transaction(referrer_id, "ref_reward", REF_REWARD, f"Реферал {username}")

        add_transaction(user_id, "welcome", balance, "Приветственный бонус")

    return balance


def update_balance(user_id: int, amount: int):
    with get_db() as db:
        db.execute("UPDATE users SET balance = balance + ?, last_active = ? WHERE user_id = ?",
                   (amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))


def add_transaction(user_id: int, t_type: str, amount: int, desc: str = ""):
    with get_db() as db:
        db.execute('''
            INSERT INTO transactions (user_id, type, amount, description, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, t_type, amount, desc, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


def get_setting(key: str, default: str = "0") -> str:
    with get_db() as db:
        cur = db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


def is_banned(user_id: int) -> bool:
    user = get_user(user_id)
    return user and user["is_banned"] == 1


def has_item(user_id: int, item_key: str) -> bool:
    with get_db() as db:
        cur = db.execute('''
            SELECT * FROM purchases
            WHERE user_id = ? AND item_key = ? AND expires_at > ?
        ''', (user_id, item_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        return cur.fetchone() is not None


def calc_mines_multiplier(total_cells: int, bombs: int, revealed: int) -> float:
    """Рассчитывает множитель для Mines по формуле честной игры."""
    safe_cells = total_cells - bombs
    if revealed <= 0 or safe_cells <= 0:
        return 1.0
    # Множитель растёт по формуле: (total_cells / safe_cells) ^ revealed * house_edge
    house_edge = 0.97  # 3% house edge
    multiplier = 1.0
    for i in range(revealed):
        multiplier *= (total_cells - i) / (safe_cells - i)
    multiplier *= house_edge
    return round(max(multiplier, 1.0), 2)


def format_balance(amount: int) -> str:
    if amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:.2f}B"
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.2f}M"
    if amount >= 1_000:
        return f"{amount / 1_000:.1f}K"
    return str(amount)


# ═══════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ БОТА
# ═══════════════════════════════════════════════════

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ═══════════════════════════════════════════════════
# FSM СОСТОЯНИЯ
# ═══════════════════════════════════════════════════

class MinesSG(StatesGroup):
    choosing_bombs = State()
    choosing_bet = State()
    playing = State()

class RouletteSG(StatesGroup):
    choosing_bet = State()

class DiceSG(StatesGroup):
    choosing_target = State()
    choosing_bet = State()

class CoinFlipSG(StatesGroup):
    choosing_bet = State()

class AdminSG(StatesGroup):
    waiting_input = State()
    waiting_broadcast = State()
    waiting_promo_code = State()
    waiting_promo_reward = State()
    waiting_promo_uses = State()
    waiting_user_id = State()
    waiting_amount = State()
    waiting_setting_key = State()
    waiting_setting_value = State()


# ═══════════════════════════════════════════════════
# КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════

def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💣 Мины", callback_data="game_mines"),
         InlineKeyboardButton(text="🎰 Рулетка", callback_data="game_roulette")],
        [InlineKeyboardButton(text="🎲 Кости", callback_data="game_dice"),
         InlineKeyboardButton(text="🪙 Монетка", callback_data="game_coinflip")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
         InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily")],
        [InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top"),
         InlineKeyboardButton(text="👥 Реферал", callback_data="referral")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
         InlineKeyboardButton(text="📖 Помощь", callback_data="help")],
    ])


def mines_bombs_kb() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for b in MINES_BOMB_OPTIONS:
        row.append(InlineKeyboardButton(text=f"{b} 💣", callback_data=f"mines_bombs_{b}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def mines_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10", callback_data="mines_bet_10"),
         InlineKeyboardButton(text="50", callback_data="mines_bet_50"),
         InlineKeyboardButton(text="100", callback_data="mines_bet_100")],
        [InlineKeyboardButton(text="500", callback_data="mines_bet_500"),
         InlineKeyboardButton(text="1000", callback_data="mines_bet_1000"),
         InlineKeyboardButton(text="5000", callback_data="mines_bet_5000")],
        [InlineKeyboardButton(text="💰 Всю сумму!", callback_data="mines_bet_all")],
        [InlineKeyboardButton(text="✏️ Своя ставка", callback_data="mines_bet_custom")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="game_mines")],
    ])


def mines_field_kb(field: list, revealed: list, bombs: int) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру 5x5 для поля Мины."""
    buttons = []
    for i in range(25):
        if i % 5 == 0:
            buttons.append([])

        if i in revealed:
            if field[i] == -1:  # бомба
                buttons[-1].append(InlineKeyboardButton(text="💥", callback_data="mines_none"))
            else:  # безопасная ячейка
                buttons[-1].append(InlineKeyboardButton(text="✅", callback_data="mines_none"))
        else:
            buttons[-1].append(InlineKeyboardButton(
                text="⬜", callback_data=f"mines_reveal_{i}"
            ))

    buttons.append([
        InlineKeyboardButton(text="💰 Забрать выигрыш!", callback_data="mines_cashout"),
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отменить игру", callback_data="mines_cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def roulette_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Красное (x2)", callback_data="roulette_red"),
         InlineKeyboardButton(text="⚫ Чёрное (x2)", callback_data="roulette_black")],
        [InlineKeyboardButton(text="🟢 Зеро (x14)", callback_data="roulette_green")],
        [InlineKeyboardButton(text="🔢 Конкретное число (x36)", callback_data="roulette_number")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")],
    ])


def roulette_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10", callback_data="rbet_10"),
         InlineKeyboardButton(text="50", callback_data="rbet_50"),
         InlineKeyboardButton(text="100", callback_data="rbet_100")],
        [InlineKeyboardButton(text="500", callback_data="rbet_500"),
         InlineKeyboardButton(text="1000", callback_data="rbet_1000"),
         InlineKeyboardButton(text="💰 Всю сумму!", callback_data="rbet_all")],
        [InlineKeyboardButton(text="✏️ Своя ставка", callback_data="rbet_custom")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="game_roulette")],
    ])


def dice_direction_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Больше (x2)", callback_data="dice_over"),
         InlineKeyboardButton(text="⬇️ Меньше (x2)", callback_data="dice_under")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")],
    ])


def coinflip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Орёл", callback_data="cf_heads"),
         InlineKeyboardButton(text="🌳 Решка", callback_data="cf_tails")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")],
    ])


def coinflip_bet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10", callback_data="cfbet_10"),
         InlineKeyboardButton(text="50", callback_data="cfbet_50"),
         InlineKeyboardButton(text="100", callback_data="cfbet_100")],
        [InlineKeyboardButton(text="500", callback_data="cfbet_500"),
         InlineKeyboardButton(text="1000", callback_data="cfbet_1000"),
         InlineKeyboardButton(text="💰 Всю сумму!", callback_data="cfbet_all")],
        [InlineKeyboardButton(text="✏️ Своя ставка", callback_data="cfbet_custom")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="game_coinflip")],
    ])


def shop_kb(user_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for key, item in SHOP_ITEMS.items():
        owned = has_item(user_id, key)
        status = " ✅" if owned else ""
        buttons.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']}{CURRENCY_EMOJI}{status}",
            callback_data=f"buy_{key}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats"),
         InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 Изменить баланс", callback_data="admin_balance"),
         InlineKeyboardButton(text="🚫 Бан/Разбан", callback_data="admin_ban")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="🎫 Промокод", callback_data="admin_promo")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
         InlineKeyboardButton(text="🗑 Очистить игру", callback_data="admin_clear_game")],
        [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")],
    ])


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: /start и /help
# ═══════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1][4:])
        except ValueError:
            pass

    user = get_user(message.from_user.id)
    if not user:
        balance = create_user(message.from_user.id, message.from_user.username or "", referrer_id)
        welcome = int(get_setting("welcome_bonus", "1000"))
        ref_text = f"\n🎁 Бонус за приглашение: +{REF_BONUS} {CURRENCY_EMOJI}" if referrer_id else ""
        await message.answer(
            f"👋 Добро пожаловать в <b>{BOT_NAME}</b>!\n\n"
            f"💎 Твой стартовый баланс: <b>{format_balance(balance)}</b> {CURRENCY_EMOJI}\n"
            f"{'🎁 Приветственный бонус: +' + format_balance(welcome) + ' ' + CURRENCY_EMOJI if not referrer_id else ''}{ref_text}\n\n"
            f"💣 Играй в Мины, рулетку, кости и выигрывай!\n"
            f"📋 Используй кнопки ниже для навигации.",
            reply_markup=main_kb()
        )
    else:
        if user["username"] != (message.from_user.username or ""):
            with get_db() as db:
                db.execute("UPDATE users SET username = ? WHERE user_id = ?",
                          (message.from_user.username or "", message.from_user.id))

        if is_banned(message.from_user.id):
            await message.answer("🚫 Вы заблокированы. Причина: " + (user["ban_reason"] or "не указана"))
            return

        await message.answer(
            f"👋 С возвращением в <b>{BOT_NAME}</b>!\n\n"
            f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
            f"Выбери игру:",
            reply_markup=main_kb()
        )

    # Кнопка админа
    if is_owner(message.from_user.id):
        await message.answer("👑 Вы — владелец бота.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel")]
        ]))


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        f"📖 <b>Помощь — {BOT_NAME}</b>\n\n"
        f"💣 <b>Мины</b> — выбери кол-во бомб, сделай ставку и открывай ячейки. Чем больше открыл — тем больше множитель. Забери выигрыш в любой момент!\n\n"
        f"🎰 <b>Рулетка</b> — красное/чёрное (x2), зеро (x14), число (x36).\n\n"
        f"🎲 <b>Кости</b> — выбери порог и направление (больше/меньше). Шанс = множитель.\n\n"
        f"🪙 <b>Монетка</b> — орёл или решка, x1.96.\n\n"
        f"🎁 <b>Ежедневный бонус</b> — заходи каждый день, streak увеличивает награду!\n\n"
        f"👥 <b>Реферал</b> — приглашай друзей и получай 5% от их ставок.\n\n"
        f"🛒 <b>Магазин</b> — покупай бонусы и усиления.\n\n"
        f"👑 Админ-команды: /admin",
        reply_markup=main_kb()
    )


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer("👑 <b>Админ-панель</b>", reply_markup=admin_kb())


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: НАВИГАЦИЯ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "back_menu")
async def cb_back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Профиль не найден. Напишите /start", reply_markup=None)
        return
    await callback.message.edit_text(
        f"🏠 <b>Главное меню</b>\n\n💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}",
        reply_markup=main_kb()
    )


@router.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return
    await callback.message.edit_text(
        f"💰 <b>Ваш баланс</b>\n\n"
        f"{CURRENCY_EMOJI} <b>{format_balance(user['balance'])}</b> {CURRENCY_NAME}\n\n"
        f"📊 Всего выиграно: <b>{format_balance(user['total_won'])}</b>\n"
        f"📊 Всего проиграно: <b>{format_balance(user['total_lost'])}</b>\n"
        f"🎮 Игр сыграно: <b>{user['games_played']}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")]
        ])
    )


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    join = user["join_date"] or "неизвестно"
    streak = user["daily_streak"] or 0

    active_items = []
    for key, item in SHOP_ITEMS.items():
        if has_item(callback.from_user.id, key):
            active_items.append(item["name"])

    items_text = "\n".join(active_items) if active_items else "нет"

    await callback.message.edit_text(
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{callback.from_user.id}</code>\n"
        f"📛 Username: @{user['username'] or 'нет'}\n"
        f"📅 В боте с: {join}\n"
        f"🔥 Стрик дейли: {streak} дней\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n"
        f"🎮 Всего игр: {user['games_played']}\n"
        f"   💣 Мин: {user['mines_played']}\n"
        f"   🎰 Рулетка: {user['roulette_played']}\n"
        f"   🎲 Кости: {user['dice_played']}\n"
        f"   🪙 Монетка: {user['coinflip_played']}\n"
        f"📊 Прибыль: <b>{format_balance(user['total_won'] - user['total_lost'])}</b>\n\n"
        f"👥 Рефералов: {user['referrals_count']}\n"
        f"🛍 Активные предметы:\n{items_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")]
        ])
    )


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(
        f"📖 <b>Помощь — {BOT_NAME}</b>\n\n"
        f"💣 <b>Мины</b> — выбери кол-во бомб, сделай ставку и открывай ячейки. "
        f"Чем больше открыл — тем больше множитель. Забери выигрыш в любой момент!\n\n"
        f"🎰 <b>Рулетка</b> — красное/чёрное (x2), зеро (x14), число (x36).\n\n"
        f"🎲 <b>Кости</b> — выбери порог и направление (больше/меньше).\n\n"
        f"🪙 <b>Монетка</b> — орёл или решка, x1.96.\n\n"
        f"🎁 <b>Ежедневный бонус</b> — заходи каждый день!\n\n"
        f"👥 <b>Реферал</b> — 5% от ставок друзей.\n\n"
        f"🛒 <b>Магазин</b> — усиления и бонусы.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")]
        ])
    )


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: ЕЖЕДНЕВНЫЙ БОНУС
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "daily")
async def cb_daily(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    now = datetime.now()
    last_daily = user["last_daily"]

    if last_daily:
        last = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S")
        if (now - last).total_seconds() < 86400:  # 24 часа
            remaining = 86400 - (now - last).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await callback.answer(f⏰ Следующий бонус через {hours}ч {minutes}мин", show_alert=True)
            return

        # Обновляем стрик
        if (now - last).days <= 1:
            new_streak = (user["daily_streak"] or 0) + 1
        else:
            new_streak = 1
    else:
        new_streak = 1

    if new_streak > DAILY_MAX_STREAK:
        new_streak = DAILY_MAX_STREAK

    bonus = DAILY_BASE + (new_streak - 1) * DAILY_STREAK_BONUS

    # Двойной бонус из магазина
    if has_item(callback.from_user.id, "x2_daily"):
        bonus *= 2

    with get_db() as db:
        db.execute('''
            UPDATE users SET balance = balance + ?, daily_streak = ?, last_daily = ?
            WHERE user_id = ?
        ''', (bonus, new_streak, now.strftime("%Y-%m-%d %H:%M:%S"), callback.from_user.id))

    add_transaction(callback.from_user.id, "daily", bonus, f"Дейли бонус (стрик {new_streak})")

    streak_bar = "🔥" * min(new_streak, 10)
    await callback.message.edit_text(
        f"🎁 <b>Ежедневный бонус!</b>\n\n"
        f"{CURRENCY_EMOJI} +<b>{format_balance(bonus)}</b> {CURRENCY_NAME}\n\n"
        f"🔥 Стрик: {new_streak} дней\n{streak_bar}\n\n"
        f"{'✨ Бонус x2 от Двойного бонуса!' if has_item(callback.from_user.id, 'x2_daily') else ''}"
        f"Заходи завтра за ещё большим вознаграждением!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
        ])
    )


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: РЕФЕРАЛ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "referral")
async def cb_referral(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"

    await callback.message.edit_text(
        f"👥 <b>Реферальная программа</b>\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>\n\n"
        f"📋 Как это работает:\n"
        f"• Приглашённый друг получает +{REF_BONUS} {CURRENCY_EMOJI}\n"
        f"• Ты получаешь +{REF_REWARD} {CURRENCY_EMOJI} за каждого друга\n"
        f"• Ты получаешь {int(REF_PERCENT*100)}% от всех ставок друзей!\n\n"
        f"📊 Твоя статистика:\n"
        f"👥 Приглашено: <b>{user['referrals_count']}</b>\n"
        f"💰 Заработано: <b>{format_balance(user['referrals_earned'])}</b> {CURRENCY_EMOJI}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="ref_copy")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")]
        ])
    )


@router.callback_query(F.data == "ref_copy")
async def cb_ref_copy(callback: CallbackQuery):
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    await callback.answer(f"Ссылка: {ref_link}", show_alert=True)


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: ТОП ИГРОКОВ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "top")
async def cb_top(callback: CallbackQuery):
    with get_db() as db:
        cur = db.execute('''
            SELECT user_id, username, balance, total_won, games_played
            FROM users WHERE is_banned = 0
            ORDER BY balance DESC LIMIT 10
        ''')
        top_balance = cur.fetchall()

        cur = db.execute('''
            SELECT user_id, username, total_won, games_played
            FROM users WHERE is_banned = 0 AND games_played > 0
            ORDER BY total_won DESC LIMIT 10
        ''')
        top_winners = cur.fetchall()

    medals = ["🥇", "🥈", "🥉"]

    text = "🏆 <b>Топ игроков</b>\n\n"
    text += "💰 <b>По балансу:</b>\n"
    for i, p in enumerate(top_balance):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = p["username"] or str(p["user_id"])
        text += f"{medal} @{name} — {format_balance(p['balance'])} {CURRENCY_EMOJI}\n"

    text += "\n🌟 <b>По выигрышам:</b>\n"
    for i, p in enumerate(top_winners):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = p["username"] or str(p["user_id"])
        text += f"{medal} @{name} — {format_balance(p['total_won'])} {CURRENCY_EMOJI}\n"

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")]
    ]))


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: МАГАЗИН
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "shop")
async def cb_shop(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    text = f"🛒 <b>Магазин</b>\n\n💰 Ваш баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
    for key, item in SHOP_ITEMS.items():
        owned = " ✅" if has_item(callback.from_user.id, key) else ""
        text += f"{item['name']}{owned}\n   {item['desc']}\n   💵 {item['price']} {CURRENCY_EMOJI} / {item['duration_days']} дн.\n\n"

    await callback.message.edit_text(text, reply_markup=shop_kb(callback.from_user.id))


@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery):
    item_key = callback.data[4:]
    if item_key not in SHOP_ITEMS:
        await callback.answer("❌ Товар не найден")
        return

    user = get_user(callback.from_user.id)
    item = SHOP_ITEMS[item_key]

    if has_item(callback.from_user.id, item_key):
        await callback.answer("✅ У вас уже есть этот предмет!", show_alert=True)
        return

    if user["balance"] < item["price"]:
        await callback.answer(f"❌ Недостаточно {CURRENCY_EMOJI}. Нужно: {item['price']}", show_alert=True)
        return

    expires = (datetime.now() + timedelta(days=item["duration_days"])).strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as db:
        db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?",
                   (item["price"], callback.from_user.id))
        db.execute('''
            INSERT INTO purchases (user_id, item_key, expires_at, purchased_at)
            VALUES (?, ?, ?, ?)
        ''', (callback.from_user.id, item_key, expires,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    add_transaction(callback.from_user.id, "purchase", -item["price"], f"Покупка {item['name']}")

    await callback.message.edit_text(
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"{item['name']}\n"
        f"Действует до: {expires}\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'] - item['price'])}</b> {CURRENCY_EMOJI}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Ещё товары", callback_data="shop")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
        ])
    )


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: МИНЫ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "game_mines")
async def cb_mines_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    # Проверяем есть ли активная игра
    with get_db() as db:
        cur = db.execute("SELECT * FROM active_mines WHERE user_id = ?", (callback.from_user.id,))
        active = cur.fetchone()

    if active:
        field = eval(active["field"])
        revealed = eval(active["revealed"]) if active["revealed"] else []
        mult = active["multiplier"]
        await callback.message.edit_text(
            f"💣 <b>Мины — Активная игра</b>\n\n"
            f"💰 Ставка: <b>{format_balance(active['bet'])}</b> {CURRENCY_EMOJI}\n"
            f"💣 Бомб: {active['bombs']}\n"
            f"📈 Множитель: <b>x{mult}</b>\n"
            f"💵 Потенциальный выигрыш: <b>{format_balance(int(active['bet'] * mult))}</b> {CURRENCY_EMOJI}\n\n"
            f"Открывай ячейки ⬇️",
            reply_markup=mines_field_kb(field, revealed, active["bombs"])
        )
        await state.set_state(MinesSG.playing)
        await state.update_data(bet=active["bet"], bombs=active["bombs"])
        return

    await callback.message.edit_text(
        f"💣 <b>Мины</b>\n\n"
        f"Выбери количество бомб на поле 5x5:\n"
        f"Чем больше бомб — тем выше множитель!",
        reply_markup=mines_bombs_kb()
    )


@router.callback_query(F.data.startswith("mines_bombs_"))
async def cb_mines_bombs(callback: CallbackQuery, state: FSMContext):
    bombs = int(callback.data.split("_")[-1])
    await state.update_data(bombs=bombs)
    user = get_user(callback.from_user.id)

    await callback.message.edit_text(
        f"💣 <b>Мины — {bombs} бомб</b>\n\n"
        f"💰 Ваш баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
        f"Выберите ставку:",
        reply_markup=mines_bet_kb()
    )
    await state.set_state(MinesSG.choosing_bet)


@router.callback_query(F.data.startswith("mines_bet_"))
async def cb_mines_bet(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    data = await state.get_data()
    bombs = data.get("bombs", 3)

    bet_str = callback.data.split("_")[-1]
    if bet_str == "custom":
        await callback.message.edit_text(
            f"✏️ <b>Введи свою ставку</b>\n\nМинимум: {MINES_MIN_BET}\nМаксимум: {user['balance']}\n\n"
            f"Отправь число или /cancel для отмены:"
        )
        await state.set_state(MinesSG.choosing_bet)
        await state.update_data(bombs=bombs, waiting_custom_bet=True)
        return

    if bet_str == "all":
        bet = user["balance"]
    else:
        bet = int(bet_str)

    if bet < MINES_MIN_BET:
        await callback.answer(f"❌ Минимальная ставка: {MINES_MIN_BET}", show_alert=True)
        return
    if bet > user["balance"]:
        await callback.answer(f"❌ Недостаточно {CURRENCY_EMOJI}", show_alert=True)
        return

    await start_mines_game(callback, bet, bombs, state)


async def start_mines_game(callback: CallbackQuery, bet: int, bombs: int, state: FSMContext):
    user = get_user(callback.from_user.id)

    # Списываем ставку
    update_balance(callback.from_user.id, -bet)
    add_transaction(callback.from_user.id, "mines_bet", -bet, f"Ставка в Мины ({bombs} бомб)")

    # Генерируем поле
    field = [0] * 25
    bomb_positions = random.sample(range(25), bombs)
    for pos in bomb_positions:
        field[pos] = -1  # -1 = бомба

    # Сохраняем в БД
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as db:
        db.execute('''
            INSERT OR REPLACE INTO active_mines (user_id, bet, bombs, revealed, field, multiplier, started_at)
            VALUES (?, ?, ?, '[]', ?, 1.0, ?)
        ''', (callback.from_user.id, bet, bombs, str(field), now))

    await callback.message.edit_text(
        f"💣 <b>Мины — Игра началась!</b>\n\n"
        f"💰 Ставка: <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}\n"
        f"💣 Бомб: {bombs}\n"
        f"📈 Множитель: <b>x1.0</b>\n\n"
        f"Открывай ячейки ⬇️",
        reply_markup=mines_field_kb(field, [], bombs)
    )
    await state.set_state(MinesSG.playing)
    await state.update_data(bet=bet, bombs=bombs)


@router.callback_query(F.data.startswith("mines_reveal_"))
async def cb_mines_reveal(callback: CallbackQuery, state: FSMContext):
    cell = int(callback.data.split("_")[-1])

    with get_db() as db:
        cur = db.execute("SELECT * FROM active_mines WHERE user_id = ?", (callback.from_user.id,))
        game = cur.fetchone()

    if not game:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return

    field = eval(game["field"])
    revealed = eval(game["revealed"]) if game["revealed"] else []

    if cell in revealed:
        await callback.answer("⬜ Уже открыто!")
        return

    revealed.append(cell)

    # Попадание на мину
    if field[cell] == -1:
        # Проверяем щит
        if has_item(callback.from_user.id, "shield"):
            with get_db() as db:
                db.execute('''
                    DELETE FROM purchases
                    WHERE user_id = ? AND item_key = 'shield'
                    LIMIT 1
                ''')
            revealed.remove(cell)
            field[cell] = 0  # Убираем бомбу
            with get_db() as db:
                db.execute('''
                    UPDATE active_mines SET revealed = ?, field = ?
                    WHERE user_id = ?
                ''', (str(revealed), str(field), callback.from_user.id))

            mult = calc_mines_multiplier(25, game["bombs"], len(revealed))
            # Бонус от амулета удачи
            if has_item(callback.from_user.id, "lucky_charm"):
                mult *= 1.05

            await callback.answer("🛡️ Щит спас вас от мины! Щит израсходован.", show_alert=True)
            await callback.message.edit_text(
                f"💣 <b>Мины</b>\n\n"
                f"💰 Ставка: <b>{format_balance(game['bet'])}</b> {CURRENCY_EMOJI}\n"
                f"💣 Бомб: {game['bombs']}\n"
                f"📈 Множитель: <b>x{mult:.2f}</b>\n"
                f"💵 Выигрыш: <b>{format_balance(int(game['bet'] * mult))}</b> {CURRENCY_EMOJI}\n\n"
                f"🛡️ Щит спас вас!\n\n"
                f"Открывай ячейки ⬇️",
                reply_markup=mines_field_kb(field, revealed, game["bombs"])
            )
            return

        # Проигрыш
        with get_db() as db:
            db.execute("DELETE FROM active_mines WHERE user_id = ?", (callback.from_user.id,))
            db.execute('''
                UPDATE users SET total_lost = total_lost + ?, games_played = games_played + 1,
                                 mines_played = mines_played + 1
                WHERE user_id = ?
            ''', (game["bet"], callback.from_user.id))

        add_transaction(callback.from_user.id, "mines_loss", -game["bet"], "Проигрыш в Минах")

        # Показываем всё поле
        all_revealed = list(range(25))
        await callback.message.edit_text(
            f"💥 <b>БАБАХ! Вы попали на мину!</b>\n\n"
            f"💰 Ставка: <b>{format_balance(game['bet'])}</b> {CURRENCY_EMOJI}\n"
            f"💣 Вы проиграли!\n\n"
            f"Поле:",
            reply_markup=mines_field_kb(field, all_revealed, game["bombs"])
        )

        # Отправляем сообщение с кнопками
        await callback.message.answer(
            f"💀 К сожалению, вы проиграли <b>{format_balance(game['bet'])}</b> {CURRENCY_EMOJI}\n\n"
            f"Попробуйте ещё раз!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💣 Играть снова", callback_data="game_mines")],
                [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
            ])
        )
        await state.clear()
        return

    # Безопасная ячейка
    mult = calc_mines_multiplier(25, game["bombs"], len(revealed))
    if has_item(callback.from_user.id, "lucky_charm"):
        mult *= 1.05

    with get_db() as db:
        db.execute('''
            UPDATE active_mines SET revealed = ?, multiplier = ?
            WHERE user_id = ?
        ''', (str(revealed), mult, callback.from_user.id))

    # Проверяем, все ли безопасные ячейки открыты
    safe_total = 25 - game["bombs"]
    if len(revealed) >= safe_total:
        # Авто-кэшаут — все безопасные открыты!
        win_amount = int(game["bet"] * mult)
        update_balance(callback.from_user.id, win_amount)

        with get_db() as db:
            db.execute("DELETE FROM active_mines WHERE user_id = ?", (callback.from_user.id,))
            db.execute('''
                UPDATE users SET total_won = total_won + ?, games_played = games_played + 1,
                                 mines_played = mines_played + 1
                WHERE user_id = ?
            ''', (win_amount, callback.from_user.id))

        add_transaction(callback.from_user.id, "mines_win", win_amount, f"Победа в Минах x{mult:.2f}")

        await callback.message.edit_text(
            f"🎉 <b>ВСЕ ЯЧЕЙКИ ОТКРЫТЫ!</b>\n\n"
            f"💰 Ставка: <b>{format_balance(game['bet'])}</b> {CURRENCY_EMOJI}\n"
            f"📈 Множитель: <b>x{mult:.2f}</b>\n"
            f"💵 Выигрыш: <b>{format_balance(win_amount)}</b> {CURRENCY_EMOJI}",
            reply_markup=mines_field_kb(field, revealed, game["bombs"])
        )

        user = get_user(callback.from_user.id)
        await callback.message.answer(
            f"🎉 Поздравляем! Вы выиграли <b>{format_balance(win_amount)}</b> {CURRENCY_EMOJI}!\n\n"
            f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💣 Играть снова", callback_data="game_mines")],
                [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
            ])
        )
        await state.clear()
        return

    await callback.message.edit_text(
        f"💣 <b>Мины</b>\n\n"
        f"💰 Ставка: <b>{format_balance(game['bet'])}</b> {CURRENCY_EMOJI}\n"
        f"💣 Бомб: {game['bombs']}\n"
        f"📈 Множитель: <b>x{mult:.2f}</b>\n"
        f"💵 Выигрыш: <b>{format_balance(int(game['bet'] * mult))}</b> {CURRENCY_EMOJI}\n\n"
        f"Открывай ячейки ⬇️",
        reply_markup=mines_field_kb(field, revealed, game["bombs"])
    )


@router.callback_query(F.data == "mines_cashout")
async def cb_mines_cashout(callback: CallbackQuery, state: FSMContext):
    with get_db() as db:
        cur = db.execute("SELECT * FROM active_mines WHERE user_id = ?", (callback.from_user.id,))
        game = cur.fetchone()

    if not game:
        await callback.answer("❌ Нет активной игры!", show_alert=True)
        return

    revealed = eval(game["revealed"]) if game["revealed"] else []
    if not revealed:
        await callback.answer("❌ Откройте хотя бы одну ячейку!", show_alert=True)
        return

    mult = game["multiplier"]
    win_amount = int(game["bet"] * mult)
    update_balance(callback.from_user.id, win_amount)

    with get_db() as db:
        db.execute("DELETE FROM active_mines WHERE user_id = ?", (callback.from_user.id,))
        db.execute('''
            UPDATE users SET total_won = total_won + ?, games_played = games_played + 1,
                             mines_played = mines_played + 1
            WHERE user_id = ?
        ''', (win_amount, callback.from_user.id))

    add_transaction(callback.from_user.id, "mines_cashout", win_amount, f"Кэшаут в Минах x{mult:.2f}")

    field = eval(game["field"])
    await callback.message.edit_text(
        f"💰 <b>Кэшаут!</b>\n\n"
        f"💣 Ставка: <b>{format_balance(game['bet'])}</b> {CURRENCY_EMOJI}\n"
        f"📈 Множитель: <b>x{mult:.2f}</b>\n"
        f"💵 Выигрыш: <b>{format_balance(win_amount)}</b> {CURRENCY_EMOJI}",
        reply_markup=mines_field_kb(field, revealed, game["bombs"])
    )

    user = get_user(callback.from_user.id)
    await callback.message.answer(
        f"✅ Вы забрали <b>{format_balance(win_amount)}</b> {CURRENCY_EMOJI}!\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💣 Играть снова", callback_data="game_mines")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
        ])
    )
    await state.clear()


@router.callback_query(F.data == "mines_cancel")
async def cb_mines_cancel(callback: CallbackQuery, state: FSMContext):
    with get_db() as db:
        cur = db.execute("SELECT * FROM active_mines WHERE user_id = ?", (callback.from_user.id,))
        game = cur.fetchone()

    if not game:
        await callback.answer("❌ Нет активной игры!")
        return

    # Возвращаем ставку
    update_balance(callback.from_user.id, game["bet"])

    with get_db() as db:
        db.execute("DELETE FROM active_mines WHERE user_id = ?", (callback.from_user.id,))

    await callback.message.edit_text(
        f"❌ <b>Игра отменена</b>\n\n💰 Ставка <b>{format_balance(game['bet'])}</b> {CURRENCY_EMOJI} возвращена.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💣 Играть снова", callback_data="game_mines")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
        ])
    )
    await state.clear()


@router.callback_query(F.data == "mines_none")
async def cb_mines_none(callback: CallbackQuery):
    await callback.answer("⬜ Ячейка уже открыта")


# Обработчик своей ставки для Mines
@router.message(MinesSG.choosing_bet)
async def msg_mines_custom_bet(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("waiting_custom_bet"):
        return

    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=None)
        return

    try:
        bet = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ Введите целое число:")
        return

    user = get_user(message.from_user.id)
    bombs = data.get("bombs", 3)

    if bet < MINES_MIN_BET:
        await message.answer(f"❌ Минимальная ставка: {MINES_MIN_BET}")
        return
    if bet > user["balance"]:
        await message.answer(f"❌ Недостаточно {CURRENCY_EMOJI}")
        return

    await state.update_data(waiting_custom_bet=False)

    # Создаём временный callback-подобный объект
    class FakeCallback:
        def __init__(self, message, from_user):
            self.message = message
            self.from_user = from_user
            self.data = ""
            self.answer = lambda *a, **kw: asyncio.sleep(0)

    fake_cb = FakeCallback(message, message.from_user)

    # Списываем ставку и начинаем
    update_balance(message.from_user.id, -bet)
    add_transaction(message.from_user.id, "mines_bet", -bet, f"Ставка в Мины ({bombs} бомб)")

    field = [0] * 25
    bomb_positions = random.sample(range(25), bombs)
    for pos in bomb_positions:
        field[pos] = -1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as db:
        db.execute('''
            INSERT OR REPLACE INTO active_mines (user_id, bet, bombs, revealed, field, multiplier, started_at)
            VALUES (?, ?, ?, '[]', ?, 1.0, ?)
        ''', (message.from_user.id, bet, bombs, str(field), now))

    await message.answer(
        f"💣 <b>Мины — Игра началась!</b>\n\n"
        f"💰 Ставка: <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}\n"
        f"💣 Бомб: {bombs}\n"
        f"📈 Множитель: <b>x1.0</b>\n\n"
        f"Открывай ячейки ⬇️",
        reply_markup=mines_field_kb(field, [], bombs)
    )
    await state.set_state(MinesSG.playing)
    await state.update_data(bet=bet, bombs=bombs)


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: РУЛЕТКА
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "game_roulette")
async def cb_roulette_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    await callback.message.edit_text(
        f"🎰 <b>Рулетка</b>\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
        f"Выберите тип ставки:",
        reply_markup=roulette_kb()
    )


@router.callback_query(F.data.startswith("roulette_"))
async def cb_roulette_choice(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]  # red, black, green, number
    multipliers = {"red": 2, "black": 2, "green": 14, "number": 36}
    mult = multipliers.get(choice, 2)

    await state.update_data(roulette_choice=choice, roulette_mult=mult)

    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"🎰 <b>Рулетка — {choice.upper()}</b> (x{mult})\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
        f"Выберите ставку:",
        reply_markup=roulette_bet_kb()
    )
    await state.set_state(RouletteSG.choosing_bet)


@router.callback_query(F.data.startswith("rbet_"))
async def cb_roulette_bet(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    data = await state.get_data()
    choice = data.get("roulette_choice", "red")
    mult = data.get("roulette_mult", 2)

    bet_str = callback.data.split("_")[-1]
    if bet_str == "custom":
        await callback.message.edit_text("✏️ Введите свою ставку:")
        await state.update_data(waiting_custom_rbet=True)
        return

    if bet_str == "all":
        bet = user["balance"]
    else:
        bet = int(bet_str)

    if bet < MINES_MIN_BET:
        await callback.answer(f"❌ Минимальная ставка: {MINES_MIN_BET}", show_alert=True)
        return
    if bet > user["balance"]:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return

    await play_roulette(callback, bet, choice, mult)


async def play_roulette(callback: CallbackQuery, bet: int, choice: str, mult: int):
    update_balance(callback.from_user.id, -bet)
    add_transaction(callback.from_user.id, "roulette_bet", -bet, "Ставка в рулетку")

    # Спин рулетки
    number = random.randint(0, 36)

    if number == 0:
        color = "🟢"
        result_type = "green"
    elif number in ROULETTE_NUMBERS_RED:
        color = "🔴"
        result_type = "red"
    else:
        color = "⚫"
        result_type = "black"

    # Проверяем выигрыш
    magnet_bonus = 1.03 if has_item(callback.from_user.id, "magnet") else 1.0

    if choice == "number":
        # Для конкретного числа - не реализуем угадывание числа, даём x36 за цвет
        won = (result_type == choice)
    else:
        won = (result_type == choice)

    if won:
        win_amount = int(bet * mult * magnet_bonus)
        update_balance(callback.from_user.id, win_amount)
        result_text = f"🎉 <b>ПОБЕДА!</b>\n\nВы выиграли <b>{format_balance(win_amount)}</b> {CURRENCY_EMOJI}!"
        add_transaction(callback.from_user.id, "roulette_win", win_amount, f"Победа в рулетке x{mult}")

        with get_db() as db:
            db.execute('''
                UPDATE users SET total_won = total_won + ?, games_played = games_played + 1,
                                 roulette_played = roulette_played + 1
                WHERE user_id = ?
            ''', (win_amount, callback.from_user.id))
    else:
        result_text = f"💀 <b>Проигрыш!</b>\n\nВы проиграли <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}."
        add_transaction(callback.from_user.id, "roulette_loss", -bet, "Проигрыш в рулетке")

        with get_db() as db:
            db.execute('''
                UPDATE users SET total_lost = total_lost + ?, games_played = games_played + 1,
                                 roulette_played = roulette_played + 1
                WHERE user_id = ?
            ''', (bet, callback.from_user.id))

    # Реферальный бонус
    user = get_user(callback.from_user.id)
    if user["referrer_id"]:
        ref_bonus = int(bet * REF_PERCENT)
        if ref_bonus > 0:
            update_balance(user["referrer_id"], ref_bonus)
            add_transaction(user["referrer_id"], "ref_percent", ref_bonus,
                          f"5% от ставки реферала")

    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"🎰 <b>Рулетка</b>\n\n"
        f"{'🎲 ' * 3} Крутим... {'🎲 ' * 3}\n\n"
        f"Выпало: <b>{color} {number}</b>\n"
        f"💰 Ставка: <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}\n"
        f"📋 Ваш выбор: {choice}\n\n"
        f"{result_text}\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Ещё раз!", callback_data="game_roulette")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
        ])
    )


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: КОСТИ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "game_dice")
async def cb_dice_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    await callback.message.edit_text(
        f"🎲 <b>Кости</b>\n\n"
        f"Выберите порог и направление:\n"
        f"Случайное число от 2 до 98.\n"
        f"Множитель зависит от шанса.",
        reply_markup=dice_direction_kb()
    )


@router.callback_query(F.data.startswith("dice_"))
async def cb_dice_direction(callback: CallbackQuery, state: FSMContext):
    direction = callback.data.split("_")[1]  # over / under
    await state.update_data(dice_direction=direction)

    # Генерируем порог
    target = random.randint(DICE_TARGET_RANGE[0] + 10, DICE_TARGET_RANGE[1] - 10)

    # Множитель на основе шанса
    if direction == "over":
        chance = (DICE_TARGET_RANGE[1] - target) / (DICE_TARGET_RANGE[1] - DICE_TARGET_RANGE[0])
    else:
        chance = (target - DICE_TARGET_RANGE[0]) / (DICE_TARGET_RANGE[1] - DICE_TARGET_RANGE[0])

    chance = max(chance, 0.01)
    mult = round(0.97 / chance, 2)

    user = get_user(callback.from_user.id)

    await callback.message.edit_text(
        f"🎲 <b>Кости</b>\n\n"
        f"🎯 Порог: <b>{target}</b>\n"
        f"{'⬆️ Больше' if direction == 'over' else '⬇️ Меньше'} {target}\n"
        f"📊 Шанс: {int(chance * 100)}%\n"
        f"📈 Множитель: <b>x{mult}</b>\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
        f"Выберите ставку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="10", callback_data=f"dicebet_10_{target}_{direction}_{mult}"),
             InlineKeyboardButton(text="50", callback_data=f"dicebet_50_{target}_{direction}_{mult}"),
             InlineKeyboardButton(text="100", callback_data=f"dicebet_100_{target}_{direction}_{mult}")],
            [InlineKeyboardButton(text="500", callback_data=f"dicebet_500_{target}_{direction}_{mult}"),
             InlineKeyboardButton(text="1000", callback_data=f"dicebet_1000_{target}_{direction}_{mult}"),
             InlineKeyboardButton(text="💰 Всю сумму!", callback_data=f"dicebet_all_{target}_{direction}_{mult}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_menu")],
        ])
    )


@router.callback_query(F.data.startswith("dicebet_"))
async def cb_dice_bet(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    parts = callback.data.split("_")
    bet_str = parts[1]
    target = int(parts[2])
    direction = parts[3]
    mult = float(parts[4])

    if bet_str == "all":
        bet = user["balance"]
    else:
        bet = int(bet_str)

    if bet < DICE_MIN_BET:
        await callback.answer(f"❌ Минимальная ставка: {DICE_MIN_BET}", show_alert=True)
        return
    if bet > user["balance"]:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return

    # Бросаем кости
    update_balance(callback.from_user.id, -bet)
    add_transaction(callback.from_user.id, "dice_bet", -bet, "Ставка в кости")

    result = random.randint(DICE_TARGET_RANGE[0], DICE_TARGET_RANGE[1])

    # Бонус золотых костей
    dice_bonus = 1.05 if has_item(callback.from_user.id, "golden_dice") else 1.0

    if direction == "over":
        won = result > target
    else:
        won = result < target

    if won:
        win_amount = int(bet * mult * dice_bonus)
        update_balance(callback.from_user.id, win_amount)
        result_text = f"🎉 <b>ПОБЕДА!</b>\n\nВы выиграли <b>{format_balance(win_amount)}</b> {CURRENCY_EMOJI}!"
        add_transaction(callback.from_user.id, "dice_win", win_amount, f"Победа в костях x{mult}")

        with get_db() as db:
            db.execute('''
                UPDATE users SET total_won = total_won + ?, games_played = games_played + 1,
                                 dice_played = dice_played + 1
                WHERE user_id = ?
            ''', (win_amount, callback.from_user.id))
    else:
        result_text = f"💀 <b>Проигрыш!</b>\n\nВы проиграли <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}."
        add_transaction(callback.from_user.id, "dice_loss", -bet, "Проигрыш в костях")

        with get_db() as db:
            db.execute('''
                UPDATE users SET total_lost = total_lost + ?, games_played = games_played + 1,
                                 dice_played = dice_played + 1
                WHERE user_id = ?
            ''', (bet, callback.from_user.id))

    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"🎲 <b>Кости</b>\n\n"
        f"🎯 Выпало: <b>{result}</b>\n"
        f"{'⬆️ Больше' if direction == 'over' else '⬇️ Меньше'} {target}\n"
        f"📈 Множитель: <b>x{mult}</b>\n"
        f"💰 Ставка: <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}\n\n"
        f"{result_text}\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Ещё раз!", callback_data="game_dice")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
        ])
    )


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: МОНЕТКА
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "game_coinflip")
async def cb_coinflip_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    await callback.message.edit_text(
        f"🪙 <b>Монетка</b>\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
        f"Выбери сторону (x1.96):",
        reply_markup=coinflip_kb()
    )


@router.callback_query(F.data.startswith("cf_"))
async def cb_coinflip_choice(callback: CallbackQuery, state: FSMContext):
    side = callback.data.split("_")[1]  # heads / tails
    await state.update_data(cf_side=side)

    user = get_user(callback.from_user.id)
    side_name = "🦅 Орёл" if side == "heads" else "🌳 Решка"

    await callback.message.edit_text(
        f"🪙 <b>Монетка</b> — {side_name}\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}\n\n"
        f"Выберите ставку:",
        reply_markup=coinflip_bet_kb()
    )


@router.callback_query(F.data.startswith("cfbet_"))
async def cb_coinflip_bet(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Напишите /start")
        return

    data = await state.get_data()
    side = data.get("cf_side", "heads")

    bet_str = callback.data.split("_")[-1]
    if bet_str == "all":
        bet = user["balance"]
    else:
        bet = int(bet_str)

    if bet < MINES_MIN_BET:
        await callback.answer(f"❌ Минимальная ставка: {MINES_MIN_BET}", show_alert=True)
        return
    if bet > user["balance"]:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return

    # Подбрасываем монетку
    update_balance(callback.from_user.id, -bet)
    add_transaction(callback.from_user.id, "cf_bet", -bet, "Ставка на монетку")

    result = random.choice(["heads", "tails"])
    result_name = "🦅 Орёл" if result == "heads" else "🌳 Решка"
    side_name = "🦅 Орёл" if side == "heads" else "🌳 Решка"

    won = (result == side)
    mult = 1.96

    if won:
        win_amount = int(bet * mult)
        update_balance(callback.from_user.id, win_amount)
        result_text = f"🎉 <b>ПОБЕДА!</b>\n\nВы выиграли <b>{format_balance(win_amount)}</b> {CURRENCY_EMOJI}!"
        add_transaction(callback.from_user.id, "cf_win", win_amount, "Победа в монетку")

        with get_db() as db:
            db.execute('''
                UPDATE users SET total_won = total_won + ?, games_played = games_played + 1,
                                 coinflip_played = coinflip_played + 1
                WHERE user_id = ?
            ''', (win_amount, callback.from_user.id))
    else:
        result_text = f"💀 <b>Проигрыш!</b>\n\nВы проиграли <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}."
        add_transaction(callback.from_user.id, "cf_loss", -bet, "Проигрыш в монетку")

        with get_db() as db:
            db.execute('''
                UPDATE users SET total_lost = total_lost + ?, games_played = games_played + 1,
                                 coinflip_played = coinflip_played + 1
                WHERE user_id = ?
            ''', (bet, callback.from_user.id))

    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"🪙 <b>Монетка</b>\n\n"
        f"🎲 Результат: <b>{result_name}</b>\n"
        f"📋 Ваш выбор: {side_name}\n"
        f"💰 Ставка: <b>{format_balance(bet)}</b> {CURRENCY_EMOJI}\n\n"
        f"{result_text}\n\n"
        f"💰 Баланс: <b>{format_balance(user['balance'])}</b> {CURRENCY_EMOJI}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🪙 Ещё раз!", callback_data="game_coinflip")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_menu")]
        ])
    )


# ═══════════════════════════════════════════════════
# ОБРАБОТЧИКИ: ПРОМОКОДЫ
# ═══════════════════════════════════════════════════

@router.message(Command("promo"))
async def cmd_promo(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("📋 Использование: /promo КОД")
        return

    code = args[1].upper()
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Напишите /start")
        return

    with get_db() as db:
        cur = db.execute("SELECT * FROM promo_codes WHERE code = ?", (code,))
        promo = cur.fetchone()

        if not promo:
            await message.answer("❌ Промокод не найден")
            return

        cur2 = db.execute("SELECT * FROM used_promos WHERE user_id = ? AND code = ?",
                          (message.from_user.id, code))
        if cur2.fetchone():
            await message.answer("❌ Вы уже использовали этот промокод")
            return

        if promo["uses_left"] <= 0:
            await message.answer("❌ Промокод исчерпан")
            return

        db.execute("UPDATE promo_codes SET uses_left = uses_left - 1, total_uses = total_uses + 1 WHERE code = ?",
                   (code,))
        db.execute('''
            INSERT INTO used_promos (user_id, code, used_at) VALUES (?, ?, ?)
        ''', (message.from_user.id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    reward = promo["reward"]
    update_balance(message.from_user.id, reward)
    add_transaction(message.from_user.id, "promo", reward, f"Промокод {code}")

    await message.answer(
        f"✅ <b>Промокод активирован!</b>\n\n"
        f"🎁 +{format_balance(reward)} {CURRENCY_EMOJI}",
        reply_markup=main_kb()
    )


# ═══════════════════════════════════════════════════
# АДМИН-ПАНЕЛЬ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        await callback.answer("🚫 Нет доступа")
        return
    await state.clear()
    await callback.message.edit_text("👑 <b>Админ-панель</b>", reply_markup=admin_kb())


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return

    with get_db() as db:
        cur = db.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cur.fetchone()["cnt"]

        cur = db.execute("SELECT COUNT(*) as cnt FROM users WHERE last_active > ?",
                        ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),))
        active_24h = cur.fetchone()["cnt"]

        cur = db.execute("SELECT SUM(balance) as total FROM users")
        total_balance = cur.fetchone()["total"] or 0

        cur = db.execute("SELECT SUM(total_won) as total FROM users")
        total_won = cur.fetchone()["total"] or 0

        cur = db.execute("SELECT SUM(total_lost) as total FROM users")
        total_lost = cur.fetchone()["total"] or 0

        cur = db.execute("SELECT SUM(games_played) as total FROM users")
        total_games = cur.fetchone()["total"] or 0

    await callback.message.edit_text(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"👥 Активных (24ч): <b>{active_24h}</b>\n"
        f"💰 Всего монет: <b>{format_balance(total_balance)}</b>\n"
        f"🏆 Всего выиграно: <b>{format_balance(total_won)}</b>\n"
        f"💀 Всего проиграно: <b>{format_balance(total_lost)}</b>\n"
        f"🎮 Всего игр: <b>{total_games}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ])
    )


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return

    with get_db() as db:
        cur = db.execute('''
            SELECT user_id, username, balance, games_played, last_active
            FROM users ORDER BY last_active DESC LIMIT 15
        ''')
        users = cur.fetchall()

    text = "👥 <b>Последние пользователи:</b>\n\n"
    for u in users:
        name = u["username"] or str(u["user_id"])
        banned = " 🚫" if is_banned(u["user_id"]) else ""
        text += f"• @{name} — {format_balance(u['balance'])} {CURRENCY_EMOJI} | {u['games_played']} игр{banned}\n"

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ]))


@router.callback_query(F.data == "admin_balance")
async def cb_admin_balance(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text(
        "💰 <b>Изменить баланс</b>\n\n"
        "Отправьте в формате:\n"
        "<code>USER_ID СУММА</code>\n\n"
        "Пример: <code>123456 5000</code>\n"
        "Для вычитания: <code>123456 -5000</code>\n\n"
        "/cancel — отмена",
    )
    await state.set_state(AdminSG.waiting_amount)


@router.message(AdminSG.waiting_amount)
async def msg_admin_balance(message: types.Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return

    if message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=None)
        return

    try:
        parts = message.text.strip().split()
        uid = int(parts[0])
        amount = int(parts[1])
    except (ValueError, IndexError):
        await message.answer("❌ Формат: USER_ID СУММА")
        return

    user = get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    update_balance(uid, amount)
    add_transaction(uid, "admin", amount, f"Админ {message.from_user.id}")

    sign = "+" if amount >= 0 else ""
    await message.answer(
        f"✅ Баланс изменён!\n\n"
        f"👤 @{user['username'] or uid}\n"
        f"💰 {sign}{format_balance(amount)} {CURRENCY_EMOJI}\n"
        f"💵 Новый баланс: {format_balance(user['balance'] + amount)} {CURRENCY_EMOJI}",
        reply_markup=admin_kb()
    )
    await state.clear()


@router.callback_query(F.data == "admin_ban")
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🚫 <b>Бан/Разбан</b>\n\n"
        "Отправьте:\n"
        "<code>ban USER_ID ПРИЧИНА</code>\n"
        "<code>unban USER_ID</code>\n\n"
        "/cancel — отмена",
    )
    await state.set_state(AdminSG.waiting_user_id)


@router.message(AdminSG.waiting_user_id)
async def msg_admin_ban(message: types.Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return

    if message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=None)
        return

    parts = message.text.strip().split()
    action = parts[0].lower()

    try:
        uid = int(parts[1])
    except (ValueError, IndexError):
        await message.answer("❌ Формат: ban/unban USER_ID")
        return

    user = get_user(uid)
    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    if action == "ban":
        reason = " ".join(parts[2:]) if len(parts) > 2 else "Нарушение правил"
        with get_db() as db:
            db.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?",
                      (reason, uid))
        await message.answer(f"🚫 Пользователь @{user['username'] or uid} забанен. Причина: {reason}",
                           reply_markup=admin_kb())
    elif action == "unban":
        with get_db() as db:
            db.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?", (uid,))
        await message.answer(f"✅ Пользователь @{user['username'] or uid} разбанен",
                           reply_markup=admin_kb())
    else:
        await message.answer("❌ Используйте ban или unban")
        return

    await state.clear()


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте текст для рассылки всем пользователям:\n"
        "/cancel — отмена",
    )
    await state.set_state(AdminSG.waiting_broadcast)


@router.message(AdminSG.waiting_broadcast)
async def msg_admin_broadcast(message: types.Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return

    if message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=None)
        return

    text = message.text
    with get_db() as db:
        cur = db.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = cur.fetchall()

    sent = failed = 0
    for u in users:
        try:
            await bot.send_message(u["user_id"], f"📢 <b>Сообщение от администрации</b>\n\n{text}")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)

    await message.answer(
        f"📢 Рассылка завершена!\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=admin_kb()
    )
    await state.clear()


@router.callback_query(F.data == "admin_promo")
async def cb_admin_promo(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🎫 <b>Создать промокод</b>\n\n"
        "Отправьте в формате:\n"
        "<code>КОД НАГРАДА КОЛ-ВО_ИСПОЛЬЗОВАНИЙ</code>\n\n"
        "Пример: <code>NEWYEAR 5000 100</code>\n"
        "/cancel — отмена",
    )
    await state.set_state(AdminSG.waiting_promo_code)


@router.message(AdminSG.waiting_promo_code)
async def msg_admin_promo(message: types.Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return

    if message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=None)
        return

    try:
        parts = message.text.strip().split()
        code = parts[0].upper()
        reward = int(parts[1])
        uses = int(parts[2])
    except (ValueError, IndexError):
        await message.answer("❌ Формат: КОД НАГРАДА КОЛ-ВО")
        return

    with get_db() as db:
        db.execute('''
            INSERT OR REPLACE INTO promo_codes (code, reward, uses_left, total_uses, created_by, created_at)
            VALUES (?, ?, ?, 0, ?, ?)
        ''', (code, reward, uses, str(message.from_user.id),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    await message.answer(
        f"✅ Промокод создан!\n\n"
        f"🎫 Код: <code>{code}</code>\n"
        f"🎁 Награда: {format_balance(reward)} {CURRENCY_EMOJI}\n"
        f"📊 Использований: {uses}",
        reply_markup=admin_kb()
    )
    await state.clear()


@router.callback_query(F.data == "admin_settings")
async def cb_admin_settings(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return

    with get_db() as db:
        cur = db.execute("SELECT * FROM bot_settings")
        settings = cur.fetchall()

    text = "⚙️ <b>Настройки</b>\n\n"
    for s in settings:
        text += f"• {s['key']}: <b>{s['value']}</b>\n"

    text += "\nДля изменения отправьте:\n<code>/setsetting КЛЮЧ ЗНАЧЕНИЕ</code>"

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ]))


@router.message(Command("setsetting"))
async def cmd_set_setting(message: types.Message):
    if not is_owner(message.from_user.id):
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("❌ Формат: /setsetting КЛЮЧ ЗНАЧЕНИЕ")
        return

    key = parts[1]
    value = " ".join(parts[2:])
    set_setting(key, value)
    await message.answer(f"✅ Настройка {key} = {value}", reply_markup=admin_kb())


@router.callback_query(F.data == "admin_clear_game")
async def cb_admin_clear_game(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return

    with get_db() as db:
        cur = db.execute("SELECT user_id, bet FROM active_mines")
        games = cur.fetchall()

        for g in games:
            update_balance(g["user_id"], g["bet"])

        db.execute("DELETE FROM active_mines")

    await callback.message.edit_text(
        f"✅ Очищено {len(games)} активных игр. Ставки возвращены.",
        reply_markup=admin_kb()
    )


# ═══════════════════════════════════════════════════
# ОТМЕНА FSM
# ═══════════════════════════════════════════════════

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    cur = await state.get_state()
    if cur:
        await state.clear()
        await message.answer("❌ Действие отменено.", reply_markup=None)
    else:
        await message.answer("Нет активного действия.")


@router.message(AdminSG)
async def admin_fsm_fallback(message: types.Message, state: FSMContext):
    await message.answer("⚠️ Ожидается ввод для админ-действия. /cancel — отменить.")


# ═══════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════

async def main():
    init_db()
    logger.info("База данных инициализирована")
    logger.info("Мины Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


async def run_gmines():
    """Запуск Мины Бота как параллельной задачи из Bot.py."""
    try:
        init_db()
        logger.info("💣 База данных Мины Бот инициализирована")
        logger.info("💣 Мины Бот запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка Мины Бот: {e}")
