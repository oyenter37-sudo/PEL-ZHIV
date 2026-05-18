#!/usr/bin/env python3
"""
Мой говорящий Навальный — Telegram Bot
Виртуальный питомец с внутренней валютой, магазином, топами и админкой.

Установка: pip install aiogram
Запуск: python main.py
"""

import asyncio
import sqlite3
import random
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ═══════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════

BOT_TOKEN = "8766561337:AAFXuRvOkWAJUsGoCvRmE8ae1tzkYu04CLo"
ADMIN_USERNAMES = {"sarafalim", "nonametipp"}
DB_PATH = "navalny_bot.db"

CURRENCY_NAME = "голоса"
CURRENCY_EMOJI = "🗳"

DECAY_RATES = {
    "hunger": 3,
    "happiness": 2,
    "energy": 2,
    "cleanliness": 2,
    "health": 1,
}

CARE_COOLDOWNS = {
    "feed": 30,
    "play": 30,
    "wash": 45,
    "sleep": 60,
    "cure": 90,
}

CARE_EFFECTS = {
    "feed":    {"hunger": 20, "exp": 10},
    "play":    {"happiness": 20, "exp": 10},
    "wash":    {"cleanliness": 25, "exp": 10},
    "sleep":   {"energy": 30, "exp": 10},
    "cure":    {"health": 25, "exp": 10},
}

CARE_CURRENCY_REWARD = 5

CATEGORY_NAMES = {
    "food": "🍔 Еда",
    "entertainment": "🎮 Развлечения",
    "hygiene": "🧼 Гигиена",
    "medicine": "💊 Медицина",
    "energy": "⚡ Энергия",
    "outfit": "👕 Наряды",
}

OUTFIT_LABELS = {
    "classic": "👔 Классический костюм",
    "outfit_sport": "👕 Спортивный костюм",
    "outfit_freedom": "✊ Футболка «Свобода»",
    "outfit_hoodie": "🧥 Толстовка с капюшоном",
    "outfit_tuxedo": "🤵 Смокинг",
    "outfit_coat": "🧣 Пальто оппозиционера",
}

LAST_FIELD_MAP = {
    "feed": "last_fed",
    "play": "last_played",
    "wash": "last_washed",
    "sleep": "last_slept",
    "cure": "last_cured",
}

STAT_FIELD_MAP = {
    "feed": "hunger",
    "play": "happiness",
    "wash": "cleanliness",
    "sleep": "energy",
    "cure": "health",
}

PHRASES = {
    "feed": [
        "Ням-ням! Как вкусно!",
        "Спасибо за еду, очень вкусно!",
        "Наконец-то покормили! Я уже голодал...",
        "Мм, обожаю! Давай ещё!",
        "Отличная еда, благодарю!",
        "Это лучше, чем доширак в камере!",
        "Хорошо, когда есть что поесть!",
    ],
    "play": [
        "Ура, играем! 🎮",
        "Так весело! Давай ещё!",
        "Ха-ха, это было здорово!",
        "Обожаю играть с тобой!",
        "Ещё! Ещё! Ещё!",
        "Жизнь — это игра, и я выигрываю!",
    ],
    "wash": [
        "Бррр, холодная вода! Но зато чистый! 🧼",
        "Чистота — залог здоровья!",
        "Ааа, мокро! Но пахну вкусно!",
        "Теперь я блестю!",
        "Свежий и чистый, как после СПА!",
        "Чистый — значит честный!",
    ],
    "sleep": [
        "Хррр... хррр... 😴",
        "Zzz... снится мне свобода...",
        "Пока-пока, иду спать... 💤",
        "Хороший сон — залог успеха!",
        "Выспался! Готов к новым делам!",
    ],
    "cure": [
        "Спасибо, мне уже лучше! 💊",
        "Ох, спасибо за лечение...",
        "Теперь я здоров, как бык!",
        "Лекарства помогли, благодарю!",
        "Восстанавливаюсь понемногу!",
        "Здоровье — главное богатство!",
    ],
    "idle": [
        "Скучно... Давай поиграем? 🥺",
        "Я хочу есть! Покорми меня! 🍔",
        "Привет! Как дела? 😊",
        "Хочу погулять! 🌊",
        "Мне одиноко... Позаботься обо мне!",
        "А давай устроим митинг? ✊",
        "Жизнь — это борьба, но я не сдаюсь! 💪",
        "Когда-нибудь всё будет хорошо! 🌅",
        "Есть хотите? А я вот хочу! 🍕",
        "Помни: каждый голос важен! 🗳",
    ],
    "sad": [
        "Мне так плохо... Позаботься обо мне 😢",
        "Я совсем ослаб... Помоги!",
        "Пожалуйста, не забывай про меня...",
        "Мне грустно и одиноко...",
        "Хоть кто-нибудь обо мне вспомнит?",
    ],
}

# ═══════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def exp_for_level(level: int) -> int:
    return level * level * 50


def init_db():
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registered_at TEXT,
            last_active TEXT,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS pets (
            user_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT 'Навальный',
            hunger INTEGER DEFAULT 70,
            happiness INTEGER DEFAULT 70,
            health INTEGER DEFAULT 80,
            energy INTEGER DEFAULT 70,
            cleanliness INTEGER DEFAULT 70,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            total_exp INTEGER DEFAULT 0,
            last_fed TEXT,
            last_played TEXT,
            last_washed TEXT,
            last_slept TEXT,
            last_cured TEXT,
            outfit TEXT DEFAULT 'classic',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS wallet (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 50,
            daily_claimed TEXT,
            work_claimed TEXT,
            total_earned INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item_id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            category TEXT NOT NULL,
            effect_type TEXT NOT NULL,
            effect_value INTEGER NOT NULL,
            emoji TEXT DEFAULT '📦'
        )""")

        c.execute("SELECT COUNT(*) FROM shop_items")
        if c.fetchone()[0] == 0:
            items = [
                # Еда
                ("Чай Лондонский", "Настоящий английский чай", 10, "food", "hunger", 10, "🍵"),
                ("Доширак", "Классика студенческой жизни", 15, "food", "hunger", 15, "🍜"),
                ("Бутерброд с икрой", "Роскошный перекус", 30, "food", "hunger", 25, "🥪"),
                ("Обед в ресторане", "Полноценный обед", 60, "food", "hunger", 40, "🍽"),
                ("Пирог мамы", "Домашний пирог с любовью", 80, "food", "hunger", 50, "🥧"),
                # Развлечения
                ("Мем про политику", "Смешной политический мем", 10, "entertainment", "happiness", 10, "😂"),
                ("Стрим на YouTube", "Посмотреть стрим", 25, "entertainment", "happiness", 20, "📺"),
                ("Прогулка по набережной", "Свежий воздух и виды", 35, "entertainment", "happiness", 25, "🌊"),
                ("Концерт", "Живой концерт любимой группы", 70, "entertainment", "happiness", 40, "🎵"),
                ("Поездка в Европу", "Путешествие мечты", 120, "entertainment", "happiness", 50, "✈️"),
                # Гигиена
                ("Душ", "Освежающий душ", 10, "hygiene", "cleanliness", 15, "🚿"),
                ("Ванна с пеной", "Расслабляющая ванна", 30, "hygiene", "cleanliness", 25, "🛁"),
                ("СПА-процедуры", "Полный СПА-день", 60, "hygiene", "cleanliness", 40, "💆"),
                # Медицина
                ("Таблетки", "От простуды", 15, "medicine", "health", 15, "💊"),
                ("Витамины", "Комплекс витаминов", 35, "medicine", "health", 25, "🩺"),
                ("Личный врач", "Осмотр у хорошего врача", 70, "medicine", "health", 40, "👨‍⚕️"),
                # Энергия
                ("Кофе", "Крепкий кофе", 10, "energy", "energy", 15, "☕"),
                ("Энергетик", "Мощный заряд бодрости", 30, "energy", "energy", 25, "⚡"),
                ("Отдых на природе", "Восстановление сил", 50, "energy", "energy", 40, "🏕"),
                # Наряды
                ("Спортивный костюм", "Удобный и стильный", 100, "outfit", "outfit_sport", 0, "👕"),
                ("Футболка «Свобода»", "С символикой", 200, "outfit", "outfit_freedom", 0, "✊"),
                ("Толстовка с капюшоном", "Для прохладных вечеров", 150, "outfit", "outfit_hoodie", 0, "🧥"),
                ("Смокинг", "Для особых случаев", 500, "outfit", "outfit_tuxedo", 0, "🤵"),
                ("Пальто оппозиционера", "Стиль и дерзость", 300, "outfit", "outfit_coat", 0, "🧣"),
            ]
            c.executemany(
                "INSERT INTO shop_items (name, description, price, category, effect_type, effect_value, emoji) VALUES (?,?,?,?,?,?,?)",
                items,
            )

        conn.commit()


# ═══════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════

def is_admin(username: str | None) -> bool:
    return bool(username) and username.lower() in ADMIN_USERNAMES


def clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def stat_bar(value: int, length: int = 10) -> str:
    filled = int(value / 100 * length)
    return "█" * filled + "░" * (length - filled)


def random_phrase(category: str) -> str:
    return random.choice(PHRASES.get(category, PHRASES["idle"]))


def apply_decay(pet: dict) -> dict:
    now = datetime.now()
    for field in ("last_fed", "last_played", "last_slept"):
        val = pet.get(field)
        if val:
            try:
                last = datetime.fromisoformat(val)
                hours = max(0, (now - last).total_seconds() / 3600)
                if hours < 0.1:
                    return pet
                for stat, rate in DECAY_RATES.items():
                    decay = rate * hours
                    if stat == "health" and (pet["hunger"] < 30 or pet["happiness"] < 30):
                        decay *= 3
                    pet[stat] = clamp(pet[stat] - int(decay))
                return pet
            except (ValueError, TypeError):
                continue
    return pet


def format_stats(pet: dict) -> str:
    bars = [
        ("🍔 Голод", pet["hunger"]),
        ("😊 Счастье", pet["happiness"]),
        ("❤️ Здоровье", pet["health"]),
        ("⚡ Энергия", pet["energy"]),
        ("🧼 Чистота", pet["cleanliness"]),
    ]
    lines = [f"{n}: [{stat_bar(v)}] {v}%" for n, v in bars]
    outfit = OUTFIT_LABELS.get(pet["outfit"], pet["outfit"])
    next_exp = exp_for_level(pet["level"])
    return (
        f"👤 <b>{pet['name']}</b>  (Уровень {pet['level']})\n"
        f"🎭 Наряд: {outfit}\n"
        f"⭐ Опыт: {pet['exp']}/{next_exp}\n\n"
        + "\n".join(lines)
    )


def check_level_up(pet: dict, conn) -> dict:
    c = conn.cursor()
    changed = False
    while pet["exp"] >= exp_for_level(pet["level"]):
        pet["exp"] -= exp_for_level(pet["level"])
        pet["level"] += 1
        changed = True
    if changed:
        c.execute("UPDATE pets SET level=?, exp=? WHERE user_id=?",
                  (pet["level"], pet["exp"], pet["user_id"]))
    return pet


# ═══════════════════════════════════════════════════
# РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ
# ═══════════════════════════════════════════════════

async def ensure_user(message: types.Message):
    uid = message.from_user.id
    uname = message.from_user.username or ""
    fname = message.from_user.first_name or ""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT is_banned, ban_reason FROM users WHERE user_id=?", (uid,))
        row = c.fetchone()
        if row and row["is_banned"]:
            return None
        now = datetime.now().isoformat()
        if not row:
            c.execute("INSERT INTO users (user_id,username,first_name,registered_at,last_active) VALUES (?,?,?,?,?)",
                      (uid, uname, fname, now, now))
            c.execute("INSERT INTO pets (user_id,last_fed,last_played,last_washed,last_slept,last_cured) VALUES (?,?,?,?,?,?)",
                      (uid, now, now, now, now, now))
            c.execute("INSERT INTO wallet (user_id,daily_claimed,work_claimed) VALUES (?,?,?)",
                      (uid, now, now))
            conn.commit()
        else:
            c.execute("UPDATE users SET last_active=?, username=?, first_name=? WHERE user_id=?",
                      (now, uname, fname, uid))
            conn.commit()
    return {"user_id": uid, "username": uname, "first_name": fname}


async def ensure_user_cb(cb: CallbackQuery):
    uid = cb.from_user.id
    uname = cb.from_user.username or ""
    fname = cb.from_user.first_name or ""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,))
        row = c.fetchone()
        if row and row["is_banned"]:
            return None
        now = datetime.now().isoformat()
        if not row:
            c.execute("INSERT INTO users (user_id,username,first_name,registered_at,last_active) VALUES (?,?,?,?,?)",
                      (uid, uname, fname, now, now))
            c.execute("INSERT INTO pets (user_id,last_fed,last_played,last_washed,last_slept,last_cured) VALUES (?,?,?,?,?,?)",
                      (uid, now, now, now, now, now))
            c.execute("INSERT INTO wallet (user_id,daily_claimed,work_claimed) VALUES (?,?,?)",
                      (uid, now, now))
            conn.commit()
    return True


# ═══════════════════════════════════════════════════
# FSM ДЛЯ АДМИНКИ
# ═══════════════════════════════════════════════════

class AdminSG(StatesGroup):
    give_uid = State()
    give_amount = State()
    take_uid = State()
    take_amount = State()
    ban_uid = State()
    ban_reason = State()
    unban_uid = State()
    broadcast_text = State()
    userinfo_uid = State()
    setstat_uid = State()
    setstat_which = State()
    setstat_value = State()
    setlevel_uid = State()
    setlevel_val = State()
    reset_uid = State()
    giveexp_uid = State()
    giveexp_val = State()
    additem_name = State()
    additem_desc = State()
    additem_price = State()
    additem_cat = State()
    additem_etype = State()
    additem_eval = State()
    additem_emoji = State()
    delitem_id = State()


# ═══════════════════════════════════════════════════
# BOT SETUP
# ═══════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ═══════════════════════════════════════════════════
# /START И ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = await ensure_user(message)
    if not user:
        await message.answer("🚫 Вы забанены и не можете использовать бота.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой Навальный", callback_data="pet_view")],
        [InlineKeyboardButton(text="🏪 Магазин", callback_data="shop_main"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inv_main")],
        [InlineKeyboardButton(text="🗳 Кошелёк", callback_data="wallet_view"),
         InlineKeyboardButton(text="🏆 Топы", callback_data="top_main")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help_view")],
    ])
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"Добро пожаловать в <b>«Мой говорящий Навальный»</b>! 🎤\n\n"
        f"Это твой виртуальный питомец. Ухаживай за ним: корми, играй, "
        f"мой, укладывай спать и лечи. Зарабатывай {CURRENCY_EMOJI} {CURRENCY_NAME} "
        f"и покупай вкусняшки в магазине!\n\n"
        f"🎯 Твой Навальный уже ждёт тебя!",
        reply_markup=kb,
    )


# ═══════════════════════════════════════════════════
# КАРТОЧКА ПИТОМЦА
# ═══════════════════════════════════════════════════

async def _render_pet(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM pets WHERE user_id=?", (user_id,))
        pet = dict(c.fetchone())
        c.execute("SELECT balance FROM wallet WHERE user_id=?", (user_id,))
        w = c.fetchone()

        pet = apply_decay(pet)
        for s in ("hunger", "happiness", "health", "energy", "cleanliness"):
            c.execute(f"UPDATE pets SET {s}=? WHERE user_id=?", (pet[s], user_id))
        conn.commit()

    if pet["hunger"] < 25 or pet["happiness"] < 25:
        phrase = random_phrase("sad")
    else:
        phrase = random_phrase("idle")

    balance = w["balance"] if w else 0
    text = f"💬 <i>«{phrase}»</i>\n\n{format_stats(pet)}\n\n🗳 Баланс: <b>{balance}</b> {CURRENCY_NAME}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍔 Покормить", callback_data="care_feed"),
         InlineKeyboardButton(text="🎮 Играть", callback_data="care_play")],
        [InlineKeyboardButton(text="🧼 Помыть", callback_data="care_wash"),
         InlineKeyboardButton(text="😴 Спать", callback_data="care_sleep")],
        [InlineKeyboardButton(text="💊 Лечить", callback_data="care_cure"),
         InlineKeyboardButton(text="🏪 Магазин", callback_data="shop_main")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inv_main"),
         InlineKeyboardButton(text="🔄 Обновить", callback_data="pet_view")],
    ])
    return text, kb


@router.message(Command("pet"))
async def cmd_pet(message: types.Message):
    user = await ensure_user(message)
    if not user:
        await message.answer("🚫 Вы забанены.")
        return
    text, kb = await _render_pet(user["user_id"])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "pet_view")
async def cb_pet_view(cb: CallbackQuery):
    if not await ensure_user_cb(cb):
        await cb.answer("🚫 Вы забанены.", show_alert=True)
        return
    text, kb = await _render_pet(cb.from_user.id)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


# ═══════════════════════════════════════════════════
# УХОД ЗА ПИТОМЦЕМ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data.startswith("care_"))
async def cb_care(cb: CallbackQuery):
    uid = cb.from_user.id
    action = cb.data[5:]  # feed / play / wash / sleep / cure

    if not await ensure_user_cb(cb):
        await cb.answer("🚫 Вы забанены.", show_alert=True)
        return

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM pets WHERE user_id=?", (uid,))
        pet = dict(c.fetchone())
        pet = apply_decay(pet)

        # кулдаун
        last_field = LAST_FIELD_MAP[action]
        try:
            last_time = datetime.fromisoformat(pet[last_field])
            elapsed_min = (datetime.now() - last_time).total_seconds() / 60
            cd = CARE_COOLDOWNS[action]
            if elapsed_min < cd:
                remain = int(cd - elapsed_min)
                await cb.answer(f"⏰ Подождите ещё {remain} мин.", show_alert=True)
                return
        except (ValueError, TypeError):
            pass

        # применить эффект
        stat = STAT_FIELD_MAP[action]
        effects = CARE_EFFECTS[action]
        new_val = clamp(pet[stat] + effects[stat])
        pet[stat] = new_val
        pet["exp"] += effects["exp"]
        pet["total_exp"] += effects["exp"]

        now_iso = datetime.now().isoformat()
        c.execute(f"UPDATE pets SET {stat}=?, exp=?, total_exp=?, {last_field}=? WHERE user_id=?",
                  (new_val, pet["exp"], pet["total_exp"], now_iso, uid))
        c.execute("UPDATE wallet SET balance=balance+?, total_earned=total_earned+? WHERE user_id=?",
                  (CARE_CURRENCY_REWARD, CARE_CURRENCY_REWARD, uid))

        pet = check_level_up(pet, conn)
        conn.commit()

    phrase = random_phrase(action)
    action_labels = {"feed": "Покормили", "play": "Поиграли", "wash": "Помыли", "sleep": "Уложили спать", "cure": "Полечили"}
    await cb.answer(f"✅ {action_labels[action]}! +{CARE_CURRENCY_REWARD} {CURRENCY_NAME}")

    text, kb = await _render_pet(uid)
    try:
        await cb.message.edit_text(f"💬 <i>«{phrase}»</i>\n\n" + text.split("\n\n", 1)[1], reply_markup=kb)
    except:
        await cb.message.answer(f"💬 <i>«{phrase}»</i>\n\n" + text.split("\n\n", 1)[1], reply_markup=kb)


# ═══════════════════════════════════════════════════
# КОШЕЛЁК И ВАЛЮТА
# ═══════════════════════════════════════════════════

async def _render_wallet(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM wallet WHERE user_id=?", (user_id,))
        w = c.fetchone()
    if not w:
        return "❌ Кошелёк не найден.", InlineKeyboardMarkup(inline_keyboard=[])
    text = (
        f"🗳 <b>Ваш кошелёк</b>\n\n"
        f"💰 Баланс: <b>{w['balance']}</b> {CURRENCY_NAME}\n"
        f"📈 Всего заработано: {w['total_earned']}\n"
        f"📉 Всего потрачено: {w['total_spent']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily_claim"),
         InlineKeyboardButton(text="💼 Работа", callback_data="work_claim")],
        [InlineKeyboardButton(text="🎲 Казино", callback_data="casino_menu")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pet_view")],
    ])
    return text, kb


@router.message(Command("wallet"))
async def cmd_wallet(message: types.Message):
    user = await ensure_user(message)
    if not user:
        await message.answer("🚫 Вы забанены.")
        return
    text, kb = await _render_wallet(user["user_id"])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "wallet_view")
async def cb_wallet_view(cb: CallbackQuery):
    if not await ensure_user_cb(cb):
        await cb.answer("🚫 Вы забанены.", show_alert=True)
        return
    text, kb = await _render_wallet(cb.from_user.id)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "daily_claim")
async def cb_daily(cb: CallbackQuery):
    uid = cb.from_user.id
    now = datetime.now()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT daily_claimed FROM wallet WHERE user_id=?", (uid,))
        row = c.fetchone()
        if row and row["daily_claimed"]:
            last = datetime.fromisoformat(row["daily_claimed"])
            if (now - last) < timedelta(hours=24):
                rem = timedelta(hours=24) - (now - last)
                h = rem.seconds // 3600
                m = (rem.seconds % 3600) // 60
                await cb.answer(f"⏰ Бонус через {h}ч {m}мин.", show_alert=True)
                return
        bonus = random.randint(20, 50)
        c.execute("UPDATE wallet SET balance=balance+?, total_earned=total_earned+?, daily_claimed=? WHERE user_id=?",
                  (bonus, bonus, now.isoformat(), uid))
        conn.commit()
    await cb.answer(f"🎁 Ежедневный бонус: +{bonus} {CURRENCY_NAME}!", show_alert=True)
    text, kb = await _render_wallet(uid)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except:
        pass


@router.callback_query(F.data == "work_claim")
async def cb_work(cb: CallbackQuery):
    uid = cb.from_user.id
    now = datetime.now()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT work_claimed FROM wallet WHERE user_id=?", (uid,))
        row = c.fetchone()
        if row and row["work_claimed"]:
            last = datetime.fromisoformat(row["work_claimed"])
            if (now - last) < timedelta(hours=1):
                m = int((timedelta(hours=1) - (now - last)).seconds // 60)
                await cb.answer(f"⏰ Работа через {m} мин.", show_alert=True)
                return
        reward = random.randint(5, 15)
        c.execute("UPDATE wallet SET balance=balance+?, total_earned=total_earned+?, work_claimed=? WHERE user_id=?",
                  (reward, reward, now.isoformat(), uid))
        conn.commit()
    await cb.answer(f"💼 Вы поработали: +{reward} {CURRENCY_NAME}!", show_alert=True)
    text, kb = await _render_wallet(uid)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except:
        pass


# ═══════════════════════════════════════════════════
# КАЗИНО
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "casino_menu")
async def cb_casino_menu(cb: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 🗳", callback_data="casino_10"),
         InlineKeyboardButton(text="25 🗳", callback_data="casino_25"),
         InlineKeyboardButton(text="50 🗳", callback_data="casino_50")],
        [InlineKeyboardButton(text="100 🗳", callback_data="casino_100"),
         InlineKeyboardButton(text="250 🗳", callback_data="casino_250")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="wallet_view")],
    ])
    try:
        await cb.message.edit_text(
            "🎲 <b>Казино</b>\n\nВыбери ставку:\n🏆 Шанс: 40%\n💰 Выигрыш: x2",
            reply_markup=kb,
        )
    except:
        pass
    await cb.answer()


@router.callback_query(F.data.startswith("casino_"))
async def cb_casino(cb: CallbackQuery):
    uid = cb.from_user.id
    bet = int(cb.data[7:])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM wallet WHERE user_id=?", (uid,))
        w = c.fetchone()
        if w["balance"] < bet:
            await cb.answer("❌ Недостаточно голосов!", show_alert=True)
            return
        if random.random() < 0.4:
            c.execute("UPDATE wallet SET balance=balance+?, total_earned=total_earned+? WHERE user_id=?",
                      (bet, bet, uid))
            msg = f"🎉 Победа! +{bet} {CURRENCY_NAME}!"
        else:
            c.execute("UPDATE wallet SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?",
                      (bet, bet, uid))
            msg = f"😢 Проигрыш! -{bet} {CURRENCY_NAME}"
        conn.commit()
    await cb.answer(msg, show_alert=True)
    text, kb = await _render_wallet(uid)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except:
        pass


# ═══════════════════════════════════════════════════
# МАГАЗИН
# ═══════════════════════════════════════════════════

async def _render_shop_main(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM wallet WHERE user_id=?", (user_id,))
        w = c.fetchone()
    bal = w["balance"] if w else 0
    text = f"🏪 <b>Магазин</b>\n\n🗳 Баланс: <b>{bal}</b> {CURRENCY_NAME}\n\nВыберите категорию:"
    buttons = [[InlineKeyboardButton(text=v, callback_data=f"shop_cat:{k}")]
               for k, v in CATEGORY_NAMES.items()]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pet_view")])
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("shop"))
async def cmd_shop(message: types.Message):
    user = await ensure_user(message)
    if not user:
        await message.answer("🚫 Вы забанены.")
        return
    text, kb = await _render_shop_main(user["user_id"])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "shop_main")
async def cb_shop_main(cb: CallbackQuery):
    if not await ensure_user_cb(cb):
        await cb.answer("🚫 Вы забанены.", show_alert=True)
        return
    text, kb = await _render_shop_main(cb.from_user.id)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except:
        pass
    await cb.answer()


@router.callback_query(F.data.startswith("shop_cat:"))
async def cb_shop_cat(cb: CallbackQuery):
    uid = cb.from_user.id
    cat = cb.data[9:]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM shop_items WHERE category=?", (cat,))
        items = c.fetchall()
        c.execute("SELECT balance FROM wallet WHERE user_id=?", (uid,))
        w = c.fetchone()
    bal = w["balance"] if w else 0
    cat_label = CATEGORY_NAMES.get(cat, cat)
    if not items:
        text = f"{cat_label}\n\nПока товаров нет."
    else:
        text = f"{cat_label}\n🗳 Баланс: <b>{bal}</b> {CURRENCY_NAME}\n\n"
        for it in items:
            text += f"{it['emoji']} <b>{it['name']}</b> — {it['price']} 🗳\n   <i>{it['description']}</i>\n\n"
    buttons = [[InlineKeyboardButton(text=f"{it['emoji']} {it['name']} — {it['price']} 🗳",
                callback_data=f"shop_buy:{it['id']}")] for it in items]
    buttons.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="shop_main")])
    try:
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except:
        pass
    await cb.answer()


@router.callback_query(F.data.startswith("shop_buy:"))
async def cb_shop_buy(cb: CallbackQuery):
    uid = cb.from_user.id
    item_id = int(cb.data[9:])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM shop_items WHERE id=?", (item_id,))
        item = c.fetchone()
        if not item:
            await cb.answer("❌ Товар не найден.", show_alert=True)
            return
        c.execute("SELECT balance FROM wallet WHERE user_id=?", (uid,))
        w = c.fetchone()
        if w["balance"] < item["price"]:
            await cb.answer(f"❌ Недостаточно! Нужно {item['price']}, у вас {w['balance']}", show_alert=True)
            return
        if item["category"] == "outfit":
            c.execute("SELECT 1 FROM inventory WHERE user_id=? AND item_id=?", (uid, item_id))
            if c.fetchone():
                await cb.answer("❌ У вас уже есть этот наряд!", show_alert=True)
                return
        c.execute("UPDATE wallet SET balance=balance-?, total_spent=total_spent+? WHERE user_id=?",
                  (item["price"], item["price"], uid))
        c.execute("INSERT INTO inventory (user_id,item_id,quantity) VALUES (?,?,1) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+1",
                  (uid, item_id))
        if item["category"] == "outfit":
            c.execute("UPDATE pets SET outfit=? WHERE user_id=?", (item["effect_type"], uid))
        conn.commit()
    await cb.answer(f"✅ Куплено: {item['emoji']} {item['name']}!", show_alert=True)
    # Обновить текущую категорию
    cat = item["category"]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM shop_items WHERE category=?", (cat,))
        items = c.fetchall()
        c.execute("SELECT balance FROM wallet WHERE user_id=?", (uid,))
        w = conn.cursor()
        w.execute("SELECT balance FROM wallet WHERE user_id=?", (uid,))
        w2 = w.fetchone()
    bal = w2["balance"] if w2 else 0
    cat_label = CATEGORY_NAMES.get(cat, cat)
    text = f"{cat_label}\n🗳 Баланс: <b>{bal}</b> {CURRENCY_NAME}\n\n"
    for it in items:
        text += f"{it['emoji']} <b>{it['name']}</b> — {it['price']} 🗳\n   <i>{it['description']}</i>\n\n"
    buttons = [[InlineKeyboardButton(text=f"{it['emoji']} {it['name']} — {it['price']} 🗳",
                callback_data=f"shop_buy:{it['id']}")] for it in items]
    buttons.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="shop_main")])
    try:
        await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except:
        pass


# ═══════════════════════════════════════════════════
# ИНВЕНТАРЬ
# ═══════════════════════════════════════════════════

@router.message(Command("inventory"))
async def cmd_inv(message: types.Message):
    user = await ensure_user(message)
    if not user:
        await message.answer("🚫 Вы забанены.")
        return
    await _show_inv(message, user["user_id"])


async def _show_inv(target, uid, edit=False):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT i.item_id, i.quantity, s.name, s.emoji, s.category, s.effect_type, s.effect_value
                      FROM inventory i JOIN shop_items s ON i.item_id=s.id
                      WHERE i.user_id=? AND i.quantity>0 ORDER BY s.category""", (uid,))
        items = c.fetchall()
    if not items:
        text = "🎒 <b>Инвентарь</b>\n\nПусто! Загляните в магазин."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏪 В магазин", callback_data="shop_main")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="pet_view")],
        ])
    else:
        text = "🎒 <b>Инвентарь</b>\n\n"
        cur_cat = ""
        buttons = []
        for it in items:
            cn = CATEGORY_NAMES.get(it["category"], it["category"])
            if cn != cur_cat:
                text += f"\n<b>{cn}</b>\n"
                cur_cat = cn
            text += f"  {it['emoji']} {it['name']} x{it['quantity']}\n"
            if it["category"] != "outfit":
                buttons.append([InlineKeyboardButton(
                    text=f"{it['emoji']} Использовать: {it['name']} (x{it['quantity']})",
                    callback_data=f"inv_use:{it['item_id']}")])
            else:
                buttons.append([InlineKeyboardButton(
                    text=f"{it['emoji']} Надеть: {it['name']}",
                    callback_data=f"inv_equip:{it['item_id']}")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="pet_view")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if edit and isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except:
            pass
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data == "inv_main")
async def cb_inv_main(cb: CallbackQuery):
    if not await ensure_user_cb(cb):
        await cb.answer("🚫 Вы забанены.", show_alert=True)
        return
    await _show_inv(cb, cb.from_user.id, edit=True)
    await cb.answer()


@router.callback_query(F.data.startswith("inv_use:"))
async def cb_inv_use(cb: CallbackQuery):
    uid = cb.from_user.id
    item_id = int(cb.data[8:])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT i.quantity, s.name, s.emoji, s.effect_type, s.effect_value, s.category
                      FROM inventory i JOIN shop_items s ON i.item_id=s.id
                      WHERE i.user_id=? AND i.item_id=?""", (uid, item_id))
        row = c.fetchone()
        if not row or row["quantity"] <= 0:
            await cb.answer("❌ Предмет не найден.", show_alert=True)
            return
        et = row["effect_type"]
        ev = row["effect_value"]
        if et in ("hunger", "happiness", "health", "energy", "cleanliness"):
            c.execute(f"SELECT {et} FROM pets WHERE user_id=?", (uid,))
            cur = c.fetchone()[et]
            c.execute(f"UPDATE pets SET {et}=? WHERE user_id=?", (clamp(cur + ev), uid))
            c.execute("UPDATE pets SET exp=exp+?, total_exp=total_exp+? WHERE user_id=?", (ev, ev, uid))
            c.execute("SELECT * FROM pets WHERE user_id=?", (uid,))
            pet = dict(c.fetchone())
            check_level_up(pet, conn)
        c.execute("UPDATE inventory SET quantity=quantity-1 WHERE user_id=? AND item_id=?", (uid, item_id))
        c.execute("DELETE FROM inventory WHERE user_id=? AND item_id=? AND quantity<=0", (uid, item_id))
        conn.commit()
    await cb.answer(f"✅ Использовано: {row['emoji']} {row['name']}!", show_alert=True)
    await _show_inv(cb, uid, edit=True)


@router.callback_query(F.data.startswith("inv_equip:"))
async def cb_inv_equip(cb: CallbackQuery):
    uid = cb.from_user.id
    item_id = int(cb.data[9:])
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT s.name, s.emoji, s.effect_type FROM inventory i
                      JOIN shop_items s ON i.item_id=s.id
                      WHERE i.user_id=? AND i.item_id=?""", (uid, item_id))
        row = c.fetchone()
        if not row:
            await cb.answer("❌ Предмет не найден.", show_alert=True)
            return
        c.execute("UPDATE pets SET outfit=? WHERE user_id=?", (row["effect_type"], uid))
        conn.commit()
    await cb.answer(f"✅ Надето: {row['emoji']} {row['name']}!", show_alert=True)
    await _show_inv(cb, uid, edit=True)


# ═══════════════════════════════════════════════════
# ТОПЫ / РЕЙТИНГ
# ═══════════════════════════════════════════════════

@router.message(Command("top"))
async def cmd_top(message: types.Message):
    user = await ensure_user(message)
    if not user:
        await message.answer("🚫 Вы забанены.")
        return
    await _show_top_menu(message)


async def _show_top_menu(target, edit=False):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Топ по уровню", callback_data="top:level")],
        [InlineKeyboardButton(text="🗳 Топ по голосам", callback_data="top:currency")],
        [InlineKeyboardButton(text="❤️ Топ по уходу", callback_data="top:care")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pet_view")],
    ])
    text = "🏆 <b>Рейтинг</b>\n\nВыберите категорию:"
    if edit and isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except:
            pass
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data == "top_main")
async def cb_top_main(cb: CallbackQuery):
    await _show_top_menu(cb, edit=True)
    await cb.answer()


@router.callback_query(F.data.startswith("top:"))
async def cb_top(cb: CallbackQuery):
    ttype = cb.data[4:]
    medals = ["🥇", "🥈", "🥉"]
    with get_db() as conn:
        c = conn.cursor()
        if ttype == "level":
            c.execute("""SELECT p.user_id, p.level, p.total_exp, u.first_name, u.username
                         FROM pets p JOIN users u ON p.user_id=u.user_id
                         WHERE u.is_banned=0 ORDER BY p.level DESC, p.total_exp DESC LIMIT 10""")
            rows = c.fetchall()
            text = "⭐ <b>Топ по уровню</b>\n\n"
            for i, r in enumerate(rows):
                m = medals[i] if i < 3 else f"{i+1}."
                n = r["first_name"] or r["username"] or f"User{r['user_id']}"
                text += f"{m} <b>{n}</b> — Ур.{r['level']} (EXP: {r['total_exp']})\n"
        elif ttype == "currency":
            c.execute("""SELECT w.user_id, w.balance, u.first_name, u.username
                         FROM wallet w JOIN users u ON w.user_id=u.user_id
                         WHERE u.is_banned=0 ORDER BY w.balance DESC LIMIT 10""")
            rows = c.fetchall()
            text = "🗳 <b>Топ по голосам</b>\n\n"
            for i, r in enumerate(rows):
                m = medals[i] if i < 3 else f"{i+1}."
                n = r["first_name"] or r["username"] or f"User{r['user_id']}"
                text += f"{m} <b>{n}</b> — {r['balance']} {CURRENCY_NAME}\n"
        elif ttype == "care":
            c.execute("""SELECT p.user_id, p.total_exp, u.first_name, u.username
                         FROM pets p JOIN users u ON p.user_id=u.user_id
                         WHERE u.is_banned=0 ORDER BY p.total_exp DESC LIMIT 10""")
            rows = c.fetchall()
            text = "❤️ <b>Топ по уходу</b>\n\n"
            for i, r in enumerate(rows):
                m = medals[i] if i < 3 else f"{i+1}."
                n = r["first_name"] or r["username"] or f"User{r['user_id']}"
                text += f"{m} <b>{n}</b> — {r['total_exp']} очков заботы\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К категориям", callback_data="top_main")],
    ])
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except:
        pass
    await cb.answer()


# ═══════════════════════════════════════════════════
# ПОМОЩЬ
# ═══════════════════════════════════════════════════

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await _show_help(message)


async def _show_help(target, edit=False):
    text = (
        "❓ <b>Помощь — Мой говорящий Навальный</b>\n\n"
        "🎮 <b>Команды:</b>\n"
        "/start — Начать игру\n"
        "/pet — Карточка питомца\n"
        "/shop — Магазин\n"
        "/inventory — Инвентарь\n"
        "/wallet — Кошелёк\n"
        "/top — Рейтинг\n"
        "/name &lt;имя&gt; — Переименовать питомца\n"
        "/help — Эта справка\n\n"
        "🐾 <b>Уход:</b>\n"
        "🍔 Покормить — голод\n"
        "🎮 Играть — счастье\n"
        "🧼 Помыть — чистота\n"
        "😴 Спать — энергия\n"
        "💊 Лечить — здоровье\n\n"
        f"🗳 <b>Валюта — {CURRENCY_NAME}:</b>\n"
        "🎁 Ежедневный бонус — раз в 24ч\n"
        "💼 Работа — раз в час\n"
        "🎲 Казино — рискни голосами\n"
        "Каждое действие ухода +5 голосов\n\n"
        "🏪 <b>Магазин:</b>\n"
        "Еда, развлечения, гигиена, медицина, энергия, наряды\n\n"
        "⭐ <b>Уровни:</b>\n"
        "Действия дают опыт → растите уровни!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="pet_view")],
    ])
    if edit and isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except:
            pass
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data == "help_view")
async def cb_help(cb: CallbackQuery):
    await _show_help(cb, edit=True)
    await cb.answer()


# ═══════════════════════════════════════════════════
# ПЕРЕИМЕНОВАНИЕ ПИТОМЦА
# ═══════════════════════════════════════════════════

@router.message(Command("name"))
async def cmd_name(message: types.Message):
    user = await ensure_user(message)
    if not user:
        await message.answer("🚫 Вы забанены.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("📝 /name <имя>\nПример: /name МойНавальный")
        return
    new_name = parts[1][:30]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE pets SET name=? WHERE user_id=?", (new_name, user["user_id"]))
        conn.commit()
    await message.answer(f"✅ Питомец теперь: <b>{new_name}</b>!")


# ═══════════════════════════════════════════════════
# АДМИН-ПАНЕЛЬ
# ═══════════════════════════════════════════════════

async def _admin_panel(target, edit=False):
    text = "🔧 <b>Админ-панель</b>\n\nВыберите действие:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="adm:stats")],
        [InlineKeyboardButton(text="💰 Дать голоса", callback_data="adm:give"),
         InlineKeyboardButton(text="💸 Забрать голоса", callback_data="adm:take")],
        [InlineKeyboardButton(text="🔨 Забанить", callback_data="adm:ban"),
         InlineKeyboardButton(text="✅ Разбанить", callback_data="adm:unban")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="👤 Инфо о юзере", callback_data="adm:userinfo")],
        [InlineKeyboardButton(text="🎯 Установить стат", callback_data="adm:setstat"),
         InlineKeyboardButton(text="⭐ Установить уровень", callback_data="adm:setlevel")],
        [InlineKeyboardButton(text="🔄 Сброс юзера", callback_data="adm:reset"),
         InlineKeyboardButton(text="🎯 Дать опыт", callback_data="adm:giveexp")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm:additem"),
         InlineKeyboardButton(text="➖ Удалить товар", callback_data="adm:delitem")],
        [InlineKeyboardButton(text="📋 Список забаненных", callback_data="adm:banlist")],
        [InlineKeyboardButton(text="📋 Все товары", callback_data="adm:allitems")],
    ])
    if edit and isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except:
            pass
    else:
        await target.answer(text, reply_markup=kb)


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.username):
        await message.answer("🚫 Доступ запрещён!")
        return
    await _admin_panel(message)


@router.callback_query(F.data.startswith("adm:"))
async def cb_admin(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.username):
        await cb.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    action = cb.data[4:]

    # ── Статистика ──
    if action == "stats":
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
            banned = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM users WHERE last_active>?",
                      ((datetime.now() - timedelta(hours=24)).isoformat(),))
            active_24h = c.fetchone()[0]
            c.execute("SELECT SUM(balance) FROM wallet")
            total_currency = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM shop_items")
            total_items = c.fetchone()[0]
        text = (
            "📊 <b>Статистика бота</b>\n\n"
            f"👥 Всего пользователей: <b>{total}</b>\n"
            f"🟢 Активных (24ч): <b>{active_24h}</b>\n"
            f"🔨 Забанено: <b>{banned}</b>\n"
            f"🗳 Всего голосов в обороте: <b>{total_currency}</b>\n"
            f"🏪 Товаров в магазине: <b>{total_items}</b>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К админке", callback_data="adm:back")],
        ])
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except:
            pass
        await cb.answer()
        return

    # ── Дать голоса ──
    if action == "give":
        await state.set_state(AdminSG.give_uid)
        await cb.message.edit_text("💰 <b>Дать голоса</b>\n\nВведите user_id пользователя:")
        await cb.answer()
        return

    # ── Забрать голоса ──
    if action == "take":
        await state.set_state(AdminSG.take_uid)
        await cb.message.edit_text("💸 <b>Забрать голоса</b>\n\nВведите user_id пользователя:")
        await cb.answer()
        return

    # ── Забанить ──
    if action == "ban":
        await state.set_state(AdminSG.ban_uid)
        await cb.message.edit_text("🔨 <b>Забанить</b>\n\nВведите user_id:")
        await cb.answer()
        return

    # ── Разбанить ──
    if action == "unban":
        await state.set_state(AdminSG.unban_uid)
        await cb.message.edit_text("✅ <b>Разбанить</b>\n\nВведите user_id:")
        await cb.answer()
        return

    # ── Рассылка ──
    if action == "broadcast":
        await state.set_state(AdminSG.broadcast_text)
        await cb.message.edit_text("📢 <b>Рассылка</b>\n\nВведите текст для рассылки (HTML поддерживается):")
        await cb.answer()
        return

    # ── Инфо о юзере ──
    if action == "userinfo":
        await state.set_state(AdminSG.userinfo_uid)
        await cb.message.edit_text("👤 <b>Инфо о юзере</b>\n\nВведите user_id:")
        await cb.answer()
        return

    # ── Установить стат ──
    if action == "setstat":
        await state.set_state(AdminSG.setstat_uid)
        await cb.message.edit_text(
            "🎯 <b>Установить стат</b>\n\nВведите user_id:\n"
            "(Статы: hunger, happiness, health, energy, cleanliness)"
        )
        await cb.answer()
        return

    # ── Установить уровень ──
    if action == "setlevel":
        await state.set_state(AdminSG.setlevel_uid)
        await cb.message.edit_text("⭐ <b>Установить уровень</b>\n\nВведите user_id:")
        await cb.answer()
        return

    # ── Сброс юзера ──
    if action == "reset":
        await state.set_state(AdminSG.reset_uid)
        await cb.message.edit_text("🔄 <b>Сброс юзера</b>\n\nВведите user_id (ВСЕ данные будут сброшены!):")
        await cb.answer()
        return

    # ── Дать опыт ──
    if action == "giveexp":
        await state.set_state(AdminSG.giveexp_uid)
        await cb.message.edit_text("🎯 <b>Дать опыт</b>\n\nВведите user_id:")
        await cb.answer()
        return

    # ── Добавить товар ──
    if action == "additem":
        await state.set_state(AdminSG.additem_name)
        await cb.message.edit_text(
            "➕ <b>Добавить товар</b>\n\nВведите название товара:\n\n"
            "Категории: food, entertainment, hygiene, medicine, energy, outfit\n"
            "Типы эффектов: hunger, happiness, health, energy, cleanliness, outfit_*"
        )
        await cb.answer()
        return

    # ── Удалить товар ──
    if action == "delitem":
        await state.set_state(AdminSG.delitem_id)
        await cb.message.edit_text("➖ <b>Удалить товар</b>\n\nВведите ID товара:")
        await cb.answer()
        return

    # ── Список забаненных ──
    if action == "banlist":
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, username, first_name, ban_reason FROM users WHERE is_banned=1")
            rows = c.fetchall()
        if not rows:
            text = "📋 <b>Забаненные</b>\n\nСписок пуст."
        else:
            text = "📋 <b>Забаненные</b>\n\n"
            for r in rows:
                n = r["first_name"] or r["username"] or f"User{r['user_id']}"
                text += f"🔨 {n} (ID: {r['user_id']}) — {r['ban_reason'] or 'нет причины'}\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К админке", callback_data="adm:back")],
        ])
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except:
            pass
        await cb.answer()
        return

    # ── Все товары ──
    if action == "allitems":
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM shop_items ORDER BY category, price")
            rows = c.fetchall()
        text = "📋 <b>Все товары</b>\n\n"
        for r in rows:
            text += f"ID:{r['id']} | {r['emoji']} {r['name']} — {r['price']} 🗳 [{r['category']}]\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К админке", callback_data="adm:back")],
        ])
        try:
            await cb.message.edit_text(text, reply_markup=kb)
        except:
            pass
        await cb.answer()
        return

    # ── Назад ──
    if action == "back":
        await _admin_panel(cb, edit=True)
        await cb.answer()
        return


# ═══════════════════════════════════════════════════
# FSM: АДМИН — ДАТЬ ГОЛОСА
# ═══════════════════════════════════════════════════

@router.message(AdminSG.give_uid)
async def admin_give_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    await state.update_data(target_uid=uid)
    await state.set_state(AdminSG.give_amount)
    await message.answer(f"Сколько голосов дать пользователю {uid}?")


@router.message(AdminSG.give_amount)
async def admin_give_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    data = await state.get_data()
    uid = data["target_uid"]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE wallet SET balance=balance+?, total_earned=total_earned+? WHERE user_id=?",
                  (amount, amount, uid))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Дано {amount} {CURRENCY_NAME} пользователю {uid}!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — ЗАБРАТЬ ГОЛОСА
# ═══════════════════════════════════════════════════

@router.message(AdminSG.take_uid)
async def admin_take_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    await state.update_data(target_uid=uid)
    await state.set_state(AdminSG.take_amount)
    await message.answer(f"Сколько голосов забрать у {uid}?")


@router.message(AdminSG.take_amount)
async def admin_take_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    data = await state.get_data()
    uid = data["target_uid"]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE wallet SET balance=MAX(0,balance-?), total_spent=total_spent+? WHERE user_id=?",
                  (amount, amount, uid))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Забрано {amount} {CURRENCY_NAME} у {uid}!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — БАН
# ═══════════════════════════════════════════════════

@router.message(AdminSG.ban_uid)
async def admin_ban_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    await state.update_data(target_uid=uid)
    await state.set_state(AdminSG.ban_reason)
    await message.answer(f"Причина бана для {uid}? (или «-» без причины)")


@router.message(AdminSG.ban_reason)
async def admin_ban_reason(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = data["target_uid"]
    reason = message.text.strip() if message.text.strip() != "-" else None
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?", (reason, uid))
        conn.commit()
    await state.clear()
    await message.answer(f"🔨 Пользователь {uid} забанен! Причина: {reason or 'не указана'}")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — РАЗБАН
# ═══════════════════════════════════════════════════

@router.message(AdminSG.unban_uid)
async def admin_unban_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=?", (uid,))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Пользователь {uid} разбанен!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — РАССЫЛКА
# ═══════════════════════════════════════════════════

@router.message(AdminSG.broadcast_text)
async def admin_broadcast(message: types.Message, state: FSMContext):
    text = message.text.strip()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned=0")
        users = c.fetchall()
    sent = 0
    failed = 0
    for u in users:
        try:
            await bot.send_message(u["user_id"], f"📢 <b>Сообщение от админа:</b>\n\n{text}")
            sent += 1
        except:
            failed += 1
    await state.clear()
    await message.answer(f"📢 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — ИНФО О ЮЗЕРЕ
# ═══════════════════════════════════════════════════

@router.message(AdminSG.userinfo_uid)
async def admin_userinfo(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        u = c.fetchone()
        c.execute("SELECT * FROM pets WHERE user_id=?", (uid,))
        p = c.fetchone()
        c.execute("SELECT * FROM wallet WHERE user_id=?", (uid,))
        w = c.fetchone()
    if not u:
        await state.clear()
        await message.answer("❌ Пользователь не найден.")
        return
    text = (
        f"👤 <b>Инфо о пользователе {uid}</b>\n\n"
        f"📋 Username: @{u['username'] or 'нет'}\n"
        f"📋 Имя: {u['first_name'] or 'нет'}\n"
        f"📋 Регистрация: {u['registered_at']}\n"
        f"📋 Последняя активность: {u['last_active']}\n"
        f"📋 Забанен: {'Да ✅' if u['is_banned'] else 'Нет'}\n"
    )
    if p:
        text += (
            f"\n🐾 <b>Питомец:</b>\n"
            f"Имя: {p['name']}\n"
            f"Уровень: {p['level']} (EXP: {p['exp']}/{exp_for_level(p['level'])})\n"
            f"Голод: {p['hunger']}% | Счастье: {p['happiness']}%\n"
            f"Здоровье: {p['health']}% | Энергия: {p['energy']}%\n"
            f"Чистота: {p['cleanliness']}%\n"
            f"Наряд: {p['outfit']}\n"
        )
    if w:
        text += (
            f"\n🗳 <b>Кошелёк:</b>\n"
            f"Баланс: {w['balance']} | Заработано: {w['total_earned']} | Потрачено: {w['total_spent']}\n"
        )
    await state.clear()
    await message.answer(text)


# ═══════════════════════════════════════════════════
# FSM: АДМИН — УСТАНОВИТЬ СТАТ
# ═══════════════════════════════════════════════════

@router.message(AdminSG.setstat_uid)
async def admin_setstat_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    await state.update_data(target_uid=uid)
    await state.set_state(AdminSG.setstat_which)
    await message.answer("Какой стат установить? (hunger / happiness / health / energy / cleanliness)")


@router.message(AdminSG.setstat_which)
async def admin_setstat_which(message: types.Message, state: FSMContext):
    stat = message.text.strip().lower()
    valid = ("hunger", "happiness", "health", "energy", "cleanliness")
    if stat not in valid:
        await message.answer(f"❌ Неверный стат. Допустимые: {', '.join(valid)}")
        return
    await state.update_data(stat_name=stat)
    await state.set_state(AdminSG.setstat_value)
    await message.answer(f"Значение для {stat} (0-100):")


@router.message(AdminSG.setstat_value)
async def admin_setstat_value(message: types.Message, state: FSMContext):
    try:
        val = clamp(int(message.text.strip()))
    except ValueError:
        await message.answer("❌ Введите число 0-100.")
        return
    data = await state.get_data()
    uid = data["target_uid"]
    stat = data["stat_name"]
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"UPDATE pets SET {stat}=? WHERE user_id=?", (val, uid))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ {stat} для {uid} установлен в {val}!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — УСТАНОВИТЬ УРОВЕНЬ
# ═══════════════════════════════════════════════════

@router.message(AdminSG.setlevel_uid)
async def admin_setlevel_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    await state.update_data(target_uid=uid)
    await state.set_state(AdminSG.setlevel_val)
    await message.answer(f"Какой уровень установить для {uid}?")


@router.message(AdminSG.setlevel_val)
async def admin_setlevel_val(message: types.Message, state: FSMContext):
    try:
        val = max(1, int(message.text.strip()))
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    data = await state.get_data()
    uid = data["target_uid"]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE pets SET level=?, exp=0 WHERE user_id=?", (val, uid))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Уровень для {uid} установлен в {val}!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — СБРОС ЮЗЕРА
# ═══════════════════════════════════════════════════

@router.message(AdminSG.reset_uid)
async def admin_reset_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    now = datetime.now().isoformat()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM inventory WHERE user_id=?", (uid,))
        c.execute("UPDATE pets SET name='Навальный', hunger=70, happiness=70, health=80, energy=70, cleanliness=70, level=1, exp=0, total_exp=0, outfit='classic', last_fed=?, last_played=?, last_washed=?, last_slept=?, last_cured=? WHERE user_id=?",
                  (now, now, now, now, now, uid))
        c.execute("UPDATE wallet SET balance=50, total_earned=0, total_spent=0, daily_claimed=?, work_claimed=? WHERE user_id=?",
                  (now, now, uid))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Данные пользователя {uid} сброшены!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — ДАТЬ ОПЫТ
# ═══════════════════════════════════════════════════

@router.message(AdminSG.giveexp_uid)
async def admin_giveexp_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (user_id).")
        return
    await state.update_data(target_uid=uid)
    await state.set_state(AdminSG.giveexp_val)
    await message.answer(f"Сколько опыта дать {uid}?")


@router.message(AdminSG.giveexp_val)
async def admin_giveexp_val(message: types.Message, state: FSMContext):
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    data = await state.get_data()
    uid = data["target_uid"]
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE pets SET exp=exp+?, total_exp=total_exp+? WHERE user_id=?", (val, val, uid))
        c.execute("SELECT * FROM pets WHERE user_id=?", (uid,))
        pet = dict(c.fetchone())
        check_level_up(pet, conn)
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Дано {val} опыта пользователю {uid}!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — ДОБАВИТЬ ТОВАР
# ═══════════════════════════════════════════════════

@router.message(AdminSG.additem_name)
async def admin_additem_name(message: types.Message, state: FSMContext):
    await state.update_data(item_name=message.text.strip())
    await state.set_state(AdminSG.additem_desc)
    await message.answer("Описание товара:")


@router.message(AdminSG.additem_desc)
async def admin_additem_desc(message: types.Message, state: FSMContext):
    await state.update_data(item_desc=message.text.strip())
    await state.set_state(AdminSG.additem_price)
    await message.answer("Цена (число):")


@router.message(AdminSG.additem_price)
async def admin_additem_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    await state.update_data(item_price=price)
    await state.set_state(AdminSG.additem_cat)
    await message.answer("Категория: food / entertainment / hygiene / medicine / energy / outfit")


@router.message(AdminSG.additem_cat)
async def admin_additem_cat(message: types.Message, state: FSMContext):
    cat = message.text.strip().lower()
    valid = ("food", "entertainment", "hygiene", "medicine", "energy", "outfit")
    if cat not in valid:
        await message.answer(f"❌ Неверная категория. Допустимые: {', '.join(valid)}")
        return
    await state.update_data(item_cat=cat)
    await state.set_state(AdminSG.additem_etype)
    await message.answer("Тип эффекта: hunger / happiness / health / energy / cleanliness / outfit_*")


@router.message(AdminSG.additem_etype)
async def admin_additem_etype(message: types.Message, state: FSMContext):
    await state.update_data(item_etype=message.text.strip())
    await state.set_state(AdminSG.additem_eval)
    await message.answer("Значение эффекта (число):")


@router.message(AdminSG.additem_eval)
async def admin_additem_eval(message: types.Message, state: FSMContext):
    try:
        ev = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    await state.update_data(item_eval=ev)
    await state.set_state(AdminSG.additem_emoji)
    await message.answer("Эмодзи товара (один символ):")


@router.message(AdminSG.additem_emoji)
async def admin_additem_emoji(message: types.Message, state: FSMContext):
    emoji = message.text.strip()[:2]
    data = await state.get_data()
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO shop_items (name,description,price,category,effect_type,effect_value,emoji) VALUES (?,?,?,?,?,?,?)",
                  (data["item_name"], data["item_desc"], data["item_price"],
                   data["item_cat"], data["item_etype"], data["item_eval"], emoji))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Товар «{data['item_name']}» добавлен!")


# ═══════════════════════════════════════════════════
# FSM: АДМИН — УДАЛИТЬ ТОВАР
# ═══════════════════════════════════════════════════

@router.message(AdminSG.delitem_id)
async def admin_delitem(message: types.Message, state: FSMContext):
    try:
        item_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число (ID).")
        return
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM shop_items WHERE id=?", (item_id,))
        row = c.fetchone()
        if not row:
            await state.clear()
            await message.answer("❌ Товар не найден.")
            return
        c.execute("DELETE FROM shop_items WHERE id=?", (item_id,))
        c.execute("DELETE FROM inventory WHERE item_id=?", (item_id,))
        conn.commit()
    await state.clear()
    await message.answer(f"✅ Товар «{row['name']}» (ID:{item_id}) удалён!")


# ═══════════════════════════════════════════════════
# ОБРАБОТКА /cancel ДЛЯ FSM
# ═══════════════════════════════════════════════════

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    cur = await state.get_state()
    if cur:
        await state.clear()
        await message.answer("❌ Действие отменено.")
    else:
        await message.answer("Нет активного действия для отмены.")


# ═══════════════════════════════════════════════════
# ОТМЕНА FSM ПРИ НЕИЗВЕСТНОМ ВВОДЕ
# ═══════════════════════════════════════════════════

@router.message(AdminSG)
async def admin_fsm_fallback(message: types.Message, state: FSMContext):
    """Если админ вводит что-то неожиданное — подсказываем /cancel"""
    await message.answer("⚠️ Ожидается ввод для админ-действия. /cancel — отменить.")


# ═══════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════

async def main():
    init_db()
    logger.info("База данных инициализирована")
    logger.info("Бот «Мой говорящий Навальный» запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

# ═══════════════════════════════════════════════════
# ФУНКЦИЯ ЗАПУСКА ИЗ Bot.py
# ═══════════════════════════════════════════════════

async def run_navalnyy():
    """Запуск бота Навального как параллельной задачи."""
    try:
        init_db()
        logger.info("🗄 База данных Навального инициализирована")
        logger.info("🎤 Бот «Мой говорящий Навальный» запускается...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка бота Навального: {e}")
