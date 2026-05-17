# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - TELEGRAM BOT v5 (Casino & Banking Update) 🦔
# =====================================
# ЧАСТЬ 1: Импорты, настройки, БД, утилиты

import asyncio
import random
import io
import os
import re
import json
from datetime import datetime, timedelta

from groq import Groq

import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, 
    InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton,
    BufferedInputFile, FSInputFile, InlineQuery, InlineQueryResultArticle, 
    InputTextMessageContent, CopyTextButton
)
from aiogram.filters import CommandStart, Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ChatMemberStatus, ButtonStyle, ChatAction

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

# 🤖 Groq AI
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
AI_CHAT_COST = 10  # Стоимость одного сообщения в Ежидзиках
AI_HISTORY_LIMIT = 3  # Запоминать последние N пар сообщений

groq_client = Groq(api_key=GROQ_API_KEY, timeout=60.0)

AI_HEDGEHOG_SYSTEM = """Ты — Говорящий Еж 🦔, милый колючий помощник в боте «Говорящий Еж». Отвечай мило, с фырканьем (фыр-фыр), иногда сворачиваясь в клубок 🦔

ХАРАКТЕР: милый, колючий, добрый, любишь яблоки и жуков, ленивый, фыркаешь, помогаешь игрокам. Говоришь коротко с эмодзи 🦔🍎🐜💎

У тебя есть ИНСТРУМЕНТЫ — два вида:
1) ИНФОРМАЦИОННЫЕ: узнать баланс, инвентарь, про ежа, банк, майнинг, муравьёв, разделы
2) ДЕЙСТВИЯ: обменять валюту, перевести деньги, забрать бонус, поймать муравья, сыграть в Ежино

Когда игрок просит ЧТО-ТО СДЕЛАТЬ — вызывай инструмент-действие! Не выдумывай результат, всегда используй инструменты.

ПРАВИЛА: 1) Отвечай как ёж — мило, с фырканьем 2) Про бота — используй инструменты 3) Не про бота — можешь ответить в образе 4) Не придумывай функции! 5) Ты настоящий ёж, не ИИ! 6) По-русски 7) Коротко, но на сложные — подробнее 8) При азартных играх предупреждаешь о риске"""

# Определение инструментов для Groq function calling
AI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_balance",
            "description": "Узнать баланс игрока: Ежидзики, Кожа слона, Алмазы, Ежкоины",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hedgehog_info",
            "description": "Узнать всё о еже: имя, класс, цвет, сытость, счастье, статус, травма",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ants_info",
            "description": "Узнать про муравьёв: количество, шанс ловли, доход в час",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_bank_info",
            "description": "Узнать про банковские вклады игрока и условия",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Узнать что есть в инвентаре игрока",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_mining_info",
            "description": "Узнать про майнинг: риги, Ежкоины, компоненты",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_referral_info",
            "description": "Узнать про рефералов: количество, заработок, ссылка",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_section_details",
            "description": "Узнать подробности о разделе бота. section: одно из [меню, ежа, финансы, казино, алмазы, перевод, обменник, сайт, звонок, ключ, друзья, бонусы, поддержка, пазл, магазин, кузница, майнинг, домашнее_казино, банк, книги, муравьи, смерть, классы, цвета, еда]",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "Название раздела для подробного описания"
                    }
                },
                "required": ["section"]
            }
        }
    },
    # ====== ИНСТРУМЕНТЫ-ДЕЙСТВИЯ ======
    {
        "type": "function",
        "function": {
            "name": "action_exchange_to_skin",
            "description": "Обменять Ежидзики на Кожу слона. Курс: 45 Ежидзиков = 1 Кожа слона. Можно обменять несколько раз за один вызов.",
            "parameters": {
                "type": "object",
                "properties": {
                    "times": {
                        "type": "integer",
                        "description": "Сколько раз обменять (1 раз = 45 ЕЖ → 1 Кожа). По умолчанию 1."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "action_exchange_to_balance",
            "description": "Обменять Кожу слона на Ежидзики. Курс: 1 Кожа слона = 45 Ежидзиков. Можно обменять несколько раз за один вызов.",
            "parameters": {
                "type": "object",
                "properties": {
                    "times": {
                        "type": "integer",
                        "description": "Сколько раз обменять (1 раз = 1 Кожа → 45 ЕЖ). По умолчанию 1."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "action_exchange_skin_to_diamonds",
            "description": "Обменять Кожу слона на Алмазы. Курс: 3 Кожи слона = 1 Алмаз. Можно обменять несколько раз.",
            "parameters": {
                "type": "object",
                "properties": {
                    "times": {
                        "type": "integer",
                        "description": "Сколько раз обменять (1 раз = 3 Кожи → 1 Алмаз). По умолчанию 1."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "action_exchange_diamonds_to_skin",
            "description": "Обменять Алмазы на Кожу слона. Курс: 1 Алмаз = 3 Кожи слона. Можно обменять несколько раз.",
            "parameters": {
                "type": "object",
                "properties": {
                    "times": {
                        "type": "integer",
                        "description": "Сколько раз обменять (1 раз = 1 Алмаз → 3 Кожи). По умолчанию 1."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "action_transfer",
            "description": "Перевести Ежидзики другому игроку. Комиссия 5%, минимум 10 Ежидзиков. Получатель: Telegram ID (число), @username, или #номер_игрока.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Получатель: Telegram ID (число), @username, или #номер_игрока"
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Сумма перевода в Ежидзиках (минимум 10)"
                    }
                },
                "required": ["recipient", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "action_claim_daily_bonus",
            "description": "Забрать ежедневный бонус (25 Ежидзиков). Доступен раз в 24 часа.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "action_catch_ant",
            "description": "Попытаться поймать муравья. Стоит 200 Ежидзиков, шанс ловли ~10%+бонусы. Каждый муравей = 10 ЕЖ/час пассивного дохода.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "action_play_ejino",
            "description": "Сыграть в Ежино — рулетку с множителями. Шансы: x0(18%), x0.5(18%), x1(18%), x1.5(18%), x2(20%), x5(8%). Ставка от 10 Ежидзиков.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bet": {
                        "type": "integer",
                        "description": "Ставка в Ежидзиках (минимум 10)"
                    }
                },
                "required": ["bet"]
            }
        }
    }
]

# Подробности о разделах бота
SECTION_DETAILS = {
    "меню": "Главное меню бота. Кнопки: Покормить🦔, Погладить🦔, Алмазы💎, Поддержка🤔, Перевод💸, Обменник♻️, Сайт🌐, Звонок📞, Пазл🧩, Ключ входа🔑, Пригласить друга👬, Бонусы🎁",
    "ежа": "Мой Ёж — управление питомцем. Покормить: еда от 2 до 111 ЕЖ, сытость 1-100%. Погладить: счастье растёт, при 100% ёж находит 50-100 ЕЖ. Сытость падает каждые 10мин! Без мебели смерть за 3 дня, с мебелью 5 дней. При 20% — предупреждение. Травма 10% при поглаживании, лечится аптечкой из магазина.",
    "финансы": "Баланс: Ежидзики👍, Кожа слона🐘, Алмазы💎. Магазин: покупка товаров. Инвентарь: ваши предметы.",
    "казино": "Ежино — 5 игр на Ежидзики: Кости🎲 (3 числа, 3 кубика), Ежино🦔 (слоты 8 эмодзи, 0x-5x), Слоты🎰 (3 барабана), Звезда🌟 (поле 5x5, 5 звёзд), Рискx10☠️ (5% шанс x10)",
    "алмазы": "Обмен Кожи слона на Алмазы: 3 КС = 1 Алмаз, 1 Алмаз = 3 КС",
    "перевод": "Перевод Ежидзиков другому игроку по ID/@username/#номер. Комиссия 5%, минимум 10 Ежидзиков.",
    "обменник": "45 Ежидзиков ↔ 1 Кожа слона (в обе стороны)",
    "сайт": "Веб-интерфейс бота: топы, кастомизация ежа, ежедневный бонус, обменник, переводы",
    "звонок": "ЭТО ТЫ! Игрок звонит ежу чтобы поговорить. 1 сообщение = 10 Ежидзиков.",
    "ключ": "Генерирует ключ для входа на сайт. Действителен 1 час. Формат: pel_XXXXXXXX",
    "друзья": "Реферальная система. Пригласивший: +20 ЕЖ, +0.3% к муравьям (макс 30%), x2 реклама 20мин, промокод на 10. Друг: 200 ЕЖ на старте вместо 0.",
    "бонусы": "Ежедневный бонус: 25 ЕЖ раз в 24ч. Реклама: 15-35 ЕЖ за просмотр (x2 после реферала 20мин). Промокоды: ввести код для награды.",
    "поддержка": "Написать в техподдержку, предложить обновление, inline промокоды (@bot pr КОД), политики использования и конфиденциальности.",
    "пазл": "Дополнительные функции: Магазин, Кузница(крафт/шахты/аукцион), Майнинг(риги/Ежкоины), Домашнее казино, Image Test",
    "магазин": "Покупка товаров за Ежидзики. Мебель (стул, стол, кровать и т.д.) снижает голод. Аптечка лечит травму. 19 товаров.",
    "кузница": "Крафт: комбинируй предметы. Плавка: переплавляй в другие. Шахты: копай с шансом найти предмет. Аукцион: торгуй с игроками.",
    "майнинг": "Сборка ригов из GPU+БП+Плата+Охлаждение. Добыча Ежкоинов. Обмен на ЕЖ/Алмазы (комиссия 10%). Поломка 5% за цикл. Электричество за ЕЖ. Макс 5 ригов. Компоненты: GT710→RTX4090.",
    "домашнее_казино": "Покупка за 300 ЕЖ. Отдельный баланс (Ежедзуки). Те же 5 игр. Продать за 150 ЕЖ.",
    "банк": "3 вклада: По требованию🐾(0.5%/день, без блокировки, от 10), Стабильный🦔(1.2%/день, 24ч блок, от 50), Премиум🏆(2%/день, 72ч блок, от 500). Макс 100к. Штраф 10% за досрочное снятие. Налог 5% на процент.",
    "книги": "Игроки пишут книги с ценой. Админ проверяет. Другие покупают — автор получает оплату.",
    "муравьи": "Поймать за 200 ЕЖ (шанс 10%+бонусы). Каждый муравей = 10 ЕЖ/час. Ежидзе-класс +10% шанс. Рефералы +0.3% каждый (макс 30%).",
    "смерть": "Сытость 0% = смерть. После: кликер(1 ЕЖ/клик, шанс 50%), попрошайничество(5-25 ЕЖ раз в 30мин), купить нового ежа.",
    "классы": "Обычный🦔(220 ЕЖ, стандарт), Ежидзе🤠(350 ЕЖ, +10% муравьи, +5% травма), Толстый🦔(300 ЕЖ, 200% сытость), Золотой🟡(600 ЕЖ, +50 бонус к награде счастья). Можно продать за 75%.",
    "цвета": "10 цветов иголок по 100 ЕЖ: ⚫Чёрный, 🟤Коричневый, ⚪Белый, 🟠Оранжевый, 🟡Золотой, 🔵Синий, 🟣Фиолетовый, 🔴Красный, 🟢Зелёный, 🌈Радужный",
    "еда": "9 видов еды: Тухлое яблоко(2 ЕЖ,+1%), Яблоко(5,+4%), Груша(6,+5%), Жук-хрущ(12,+10%), Молоко кота(30,+20%), Молоко(39,+25%), Хлеб(59,+40%), Капуста(70,+50%), Электрический робот(111,+100%)"
}


async def ai_tool_get_balance(user_id: int) -> str:
    user = await get_user(user_id)
    if not user:
        return "Игрок не найден"
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT ezhcoins FROM mining_state WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            ezhcoins = row[0] if row else 0
    return f"Баланс: {user['balance']} Ежидзиков👍, {user['elephant_skin']} Кожи слона🐘, {user['diamonds']} Алмазов💎, {ezhcoins:.1f} Ежкоинов"


async def ai_tool_get_hedgehog_info(user_id: int) -> str:
    user = await get_user(user_id)
    if not user:
        return "Игрок не найден"
    class_names = {"normal": "Обычный 🦔", "ejidze": "Ежидзе 🤠", "fat": "Толстый 🦔", "golden": "Золотой 🟡"}
    cls = class_names.get(user['hedgehog_class'], user['hedgehog_class'])
    status = "живой 🟢" if user['status'] == 'alive' else "мёртвый 💀"
    injured = "Да, нужна аптечка!" if user['is_injured'] else "Нет"
    return (f"Имя: {user['hedgehog_name']}, Класс: {cls}, Цвет: {user['hedgehog_color']}\n"
            f"Сытость: {user['satiety']:.0f}%, Счастье: {user['happiness']:.0f}%\n"
            f"Статус: {status}, Травма: {injured}")


async def ai_tool_get_ants_info(user_id: int) -> str:
    user = await get_user(user_id)
    if not user:
        return "Игрок не найден"
    chance = user['ant_chance']
    income = user['ants'] * 10
    return f"Муравьёв: {user['ants']}, Шанс ловли: {chance:.1f}%, Доход: {income} ЕЖ/час"


async def ai_tool_get_bank_info(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bank_deposits WHERE user_id = ? AND status = 'active'", (user_id,)) as cursor:
            deposits = await cursor.fetchall()
    if not deposits:
        return "Нет активных вкладов. Условия: 🐾0.5%/день(от 10), 🦔1.2%/день 24ч блок(от 50), 🏆2%/день 72ч блок(от 500). Макс 100к, штраф 10%, налог 5%"
    lines = []
    for d in deposits:
        lines.append(f"{d['deposit_type']}: {d['amount']} ЕЖ, начислено {d['accrued']} ЕЖ, статус: {d['status']}")
    return "Ваши вклады:\n" + "\n".join(lines)


async def ai_tool_get_inventory(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT si.name, i.quantity FROM inventory i JOIN shop_items si ON i.item_id = si.id WHERE i.user_id = ? AND i.quantity > 0",
            (user_id,)
        ) as cursor:
            items = await cursor.fetchall()
    if not items:
        return "Инвентарь пуст"
    return "Инвентарь: " + ", ".join(f"{it['name']} x{it['quantity']}" for it in items)


async def ai_tool_get_mining_info(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_state WHERE user_id = ?", (user_id,)) as cursor:
            state = await cursor.fetchone()
        async with db.execute("SELECT COUNT(*) as cnt FROM mining_rigs WHERE user_id = ?", (user_id,)) as cursor:
            rigs_count = (await cursor.fetchone())['cnt']
    if not state or rigs_count == 0:
        return "Майнинг не настроен. Нужно: купить GPU+БП+Плата, собрать риг. Компоненты от GT710 до RTX4090. Макс 5 ригов."
    return f"Ригов: {rigs_count}, Ежкоинов: {state['ezhcoins']:.1f}, Майнит: {'Да' if state['is_mining'] else 'Нет'}, Всего намайнено: {state['total_mined']:.1f}"


async def ai_tool_get_referral_info(user_id: int) -> str:
    user = await get_user(user_id)
    if not user:
        return "Игрок не найден"
    bot_username = await _get_bot_username()
    link = f"https://t.me/{bot_username}?start={user_id}"
    return (f"Рефералов: {user['referrals_count']}, Заработано: {user['referrals_earned']} ЕЖ\n"
            f"Ссылка: {link}")


async def ai_tool_get_section_details(user_id: int, section: str) -> str:
    return SECTION_DETAILS.get(section.lower(), f"Раздел '{section}' не найден. Доступные: " + ", ".join(SECTION_DETAILS.keys()))


# ====== ФУНКЦИИ ИНСТРУМЕНТОВ-ДЕЙСТВИЙ ======

async def ai_tool_action_exchange_to_skin(user_id: int, times: int = 1) -> str:
    """Обменять Ежидзики на Кожу слона: 45 ЕЖ → 1 Кожа. Можно несколько раз."""
    times = max(1, min(times, 100))  # Лимит 100 за раз
    cost = 45 * times
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET balance = balance - ?, elephant_skin = elephant_skin + ? WHERE user_id = ? AND balance >= ?",
            (cost, times, user_id, cost)
        )
        if cursor.rowcount == 0:
            user = await get_user(user_id)
            bal = user['balance'] if user else 0
            return f"❌ Недостаточно Ежидзиков! Нужно {cost}, у тебя {bal}"
        await db.commit()
    user = await get_user(user_id)
    return f"✅ Обмен выполнен! -{cost} Ежидзиков👍, +{times} Кожи слона🐘. Осталось: {user['balance']} ЕЖ, {user['elephant_skin']} КС"


async def ai_tool_action_exchange_to_balance(user_id: int, times: int = 1) -> str:
    """Обменять Кожу слона на Ежидзики: 1 Кожа → 45 ЕЖ. Можно несколько раз."""
    times = max(1, min(times, 100))
    reward = 45 * times
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET elephant_skin = elephant_skin - ?, balance = balance + ? WHERE user_id = ? AND elephant_skin >= ?",
            (times, reward, user_id, times)
        )
        if cursor.rowcount == 0:
            user = await get_user(user_id)
            skin = user['elephant_skin'] if user else 0
            return f"❌ Недостаточно Кожи слона! Нужно {times}, у тебя {skin}"
        await db.commit()
    user = await get_user(user_id)
    return f"✅ Обмен выполнен! -{times} Кожи слона🐘, +{reward} Ежидзиков👍. Осталось: {user['balance']} ЕЖ, {user['elephant_skin']} КС"


async def ai_tool_action_exchange_skin_to_diamonds(user_id: int, times: int = 1) -> str:
    """Обменять Кожу слона на Алмазы: 3 Кожи → 1 Алмаз. Можно несколько раз."""
    times = max(1, min(times, 100))
    skin_cost = 3 * times
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET elephant_skin = elephant_skin - ?, diamonds = diamonds + ? WHERE user_id = ? AND elephant_skin >= ?",
            (skin_cost, times, user_id, skin_cost)
        )
        if cursor.rowcount == 0:
            user = await get_user(user_id)
            skin = user['elephant_skin'] if user else 0
            return f"❌ Недостаточно Кожи слона! Нужно {skin_cost} (3 за алмаз × {times}), у тебя {skin}"
        await db.commit()
    user = await get_user(user_id)
    return f"✅ Обмен выполнен! -{skin_cost} Кожи слона🐘, +{times} Алмазов💎. Осталось: {user['elephant_skin']} КС, {user['diamonds']} 💎"


async def ai_tool_action_exchange_diamonds_to_skin(user_id: int, times: int = 1) -> str:
    """Обменять Алмазы на Кожу слона: 1 Алмаз → 3 Кожи. Можно несколько раз."""
    times = max(1, min(times, 100))
    skin_reward = 3 * times
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET diamonds = diamonds - ?, elephant_skin = elephant_skin + ? WHERE user_id = ? AND diamonds >= ?",
            (times, skin_reward, user_id, times)
        )
        if cursor.rowcount == 0:
            user = await get_user(user_id)
            dia = user['diamonds'] if user else 0
            return f"❌ Недостаточно Алмазов! Нужно {times}, у тебя {dia}"
        await db.commit()
    user = await get_user(user_id)
    return f"✅ Обмен выполнен! -{times} Алмазов💎, +{skin_reward} Кожи слона🐘. Осталось: {user['diamonds']} 💎, {user['elephant_skin']} КС"


async def ai_tool_action_transfer(user_id: int, recipient: str, amount: int) -> str:
    """Перевести Ежидзики другому игроку. Комиссия 5%, минимум 10."""
    if amount < 10:
        return "❌ Минимальная сумма перевода — 10 Ежидзиков!"
    
    # Ищем получателя
    target = await find_user_flexible(recipient)
    if not target:
        return f"❌ Игрок '{recipient}' не найден! Укажи ID, @username или #номер"
    
    if target['user_id'] == user_id:
        return "❌ Нельзя переводить самому себе!"
    
    commission = max(1, int(amount * 0.05))
    to_receive = amount - commission
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
            (amount, user_id, amount)
        )
        if cursor.rowcount == 0:
            user = await get_user(user_id)
            return f"❌ Недостаточно средств! Нужно {amount}, у тебя {user['balance'] if user else 0}"
        
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (to_receive, target['user_id']))
        await db.commit()
    
    return (f"✅ Перевод выполнен!\n"
            f"📤 Получатель: @{target['username']} (#{target['player_number']:04d})\n"
            f"💰 Списано: {amount} ЕЖ\n"
            f"📉 Комиссия: {commission} ЕЖ (5%)\n"
            f"📥 Зачислено: {to_receive} ЕЖ")


async def ai_tool_action_claim_daily_bonus(user_id: int) -> str:
    """Забрать ежедневный бонус (25 ЕЖ, раз в 24ч)."""
    user = await get_user(user_id)
    if not user:
        return "Игрок не найден"
    
    now = datetime.now()
    last_daily = user['last_daily']
    
    if last_daily:
        try:
            last_daily_dt = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S")
            if now - last_daily_dt < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_daily_dt)
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                return f"⏰ Бонус уже забран! Следующий через {hours}ч {minutes}мин"
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
    
    user = await get_user(user_id)
    return f"✅ Ежедневный бонус получен! +{bonus_amount} Ежидзиков👍. Баланс: {user['balance']} ЕЖ"


async def ai_tool_action_catch_ant(user_id: int) -> str:
    """Попытаться поймать муравья (200 ЕЖ, шанс ~10%+)."""
    user = await get_user(user_id)
    if not user:
        return "Игрок не найден"
    
    ant_cost = int(await get_setting("ant_catch_cost", "200"))
    ant_income = int(await get_setting("ant_income", "10"))
    
    if user['balance'] < ant_cost:
        return f"❌ Недостаточно Ежидзиков! Нужно {ant_cost}, у тебя {user['balance']}"
    
    # Списываем стоимость
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (ant_cost, user_id))
        await db.commit()
    
    # Считаем шанс
    ant_chance = user['ant_chance']
    if user['hedgehog_class'] == 'ejidze':
        ant_chance += 10.0
    
    if random.random() * 100 < ant_chance:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET ants = ants + 1 WHERE user_id = ?", (user_id,))
            await db.commit()
        user = await get_user(user_id)
        total_income = user['ants'] * ant_income
        return (f"🎉 УРА! Муравей пойман! 🐜\n"
                f"Теперь муравьёв: {user['ants']}\n"
                f"Доход: {total_income} ЕЖ/час\n"
                f"💰 Баланс: {user['balance']} ЕЖ")
    else:
        user = await get_user(user_id)
        return (f"😔 Муравей убежал... Фыр-фыр!\n"
                f"Шанс ловли: {ant_chance:.1f}%\n"
                f"Попробуй ещё раз!\n"
                f"💰 Баланс: {user['balance']} ЕЖ")


async def ai_tool_action_play_ejino(user_id: int, bet: int) -> str:
    """Сыграть в Ежино — рулетка с множителями (x0-x5)."""
    if bet < 10:
        return "❌ Минимальная ставка — 10 Ежидзиков!"
    if bet > 10000:
        return "❌ Максимальная ставка — 10000 Ежидзиков!"
    
    user = await get_user(user_id)
    if not user:
        return "Игрок не найден"
    
    if user['balance'] < bet:
        return f"❌ Недостаточно Ежидзиков! Ставка {bet}, у тебя {user['balance']}"
    
    # Крутим рулетку (те же множители что в основной игре)
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
        cursor = await db.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
            (bet, user_id, bet)
        )
        if cursor.rowcount == 0:
            return f"❌ Недостаточно Ежидзиков! Ставка {bet}, у тебя недостаточно средств"
        
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
    
    user = await get_user(user_id)
    
    if multiplier >= 5:
        result_emoji = "🔥🎉🔥 ДЖЕКПОТ!!!"
    elif multiplier >= 2:
        result_emoji = "🎉 Победа!"
    elif multiplier >= 1:
        result_emoji = "😐 Возврат"
    elif multiplier >= 0.5:
        result_emoji = "😔 Частичный возврат"
    else:
        result_emoji = "💔 Проигрыш..."
    
    return (f"🦔 ЕЖИНО — результат!\n"
            f"Ставка: {bet} ЕЖ | Множитель: ×{multiplier}\n"
            f"{result_emoji}\n"
            f"Выигрыш: {win} ЕЖ | Профит: {'+' if profit >= 0 else ''}{profit} ЕЖ\n"
            f"💰 Баланс: {user['balance']} ЕЖ")


# Маппинг имен инструментов на функции
AI_TOOL_FUNCTIONS = {
    # Информационные
    "get_balance": ai_tool_get_balance,
    "get_hedgehog_info": ai_tool_get_hedgehog_info,
    "get_ants_info": ai_tool_get_ants_info,
    "get_bank_info": ai_tool_get_bank_info,
    "get_inventory": ai_tool_get_inventory,
    "get_mining_info": ai_tool_get_mining_info,
    "get_referral_info": ai_tool_get_referral_info,
    "get_section_details": ai_tool_get_section_details,
    # Действия — обмен
    "action_exchange_to_skin": ai_tool_action_exchange_to_skin,
    "action_exchange_to_balance": ai_tool_action_exchange_to_balance,
    "action_exchange_skin_to_diamonds": ai_tool_action_exchange_skin_to_diamonds,
    "action_exchange_diamonds_to_skin": ai_tool_action_exchange_diamonds_to_skin,
    # Действия — перевод
    "action_transfer": ai_tool_action_transfer,
    # Действия — бонусы
    "action_claim_daily_bonus": ai_tool_action_claim_daily_bonus,
    # Действия — муравьи
    "action_catch_ant": ai_tool_action_catch_ant,
    # Действия — казино
    "action_play_ejino": ai_tool_action_play_ejino,
}

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
# 🤠 КЛАССЫ ЕЖЕЙ (v5)
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
# 🥕 ЕДА (v5)
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
        # Миграция: добавляем used_at если отсутствует
        try:
            await db.execute('ALTER TABLE used_promocodes ADD COLUMN used_at TEXT DEFAULT NULL')
        except Exception:
            pass  # колонка уже существует
        
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

        # v5 Table for Books
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

        # Кузница: предметы
        await db.execute('''
            CREATE TABLE IF NOT EXISTS forge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                default_price INTEGER DEFAULT 0,
                currency TEXT DEFAULT 'balance',
                mine_chance REAL DEFAULT 0,
                mine_time INTEGER DEFAULT 0,
                auctionable INTEGER DEFAULT 0,
                smeltable INTEGER DEFAULT 0,
                smelt_result_id INTEGER DEFAULT NULL,
                smelt_result_qty INTEGER DEFAULT 1,
                created_at TEXT
            )
        ''')

        # Кузница: инвентарь игроков (отдельный от магазинного)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS forge_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 0,
                UNIQUE(user_id, item_id),
                FOREIGN KEY (item_id) REFERENCES forge_items(id)
            )
        ''')

        # Кузница: крафты
        await db.execute('''
            CREATE TABLE IF NOT EXISTS crafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                result_item_id INTEGER NOT NULL,
                result_qty INTEGER DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (result_item_id) REFERENCES forge_items(id)
            )
        ''')

        # Кузница: ингредиенты для крафтов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS craft_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                craft_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (craft_id) REFERENCES crafts(id),
                FOREIGN KEY (item_id) REFERENCES forge_items(id)
            )
        ''')

        # Кузница: аукцион (выставленные лоты)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS auction_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                price INTEGER NOT NULL,
                currency TEXT DEFAULT 'balance',
                is_standard INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT
            )
        ''')

        # Кузница: состояние шахты игрока
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mine_state (
                user_id INTEGER PRIMARY KEY,
                mining_until TEXT DEFAULT NULL,
                cooldown_until TEXT DEFAULT NULL,
                current_item_id INTEGER DEFAULT NULL
            )
        ''')

        # Майнинг: каталог комплектующих
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mining_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                comp_type TEXT NOT NULL,
                price INTEGER NOT NULL,
                currency TEXT DEFAULT 'balance',
                mh_rate REAL DEFAULT 0,
                power_w INTEGER DEFAULT 0,
                gpu_slots INTEGER DEFAULT 0,
                break_reduction REAL DEFAULT 0,
                UNIQUE(name)
            )
        ''')

        # Майнинг: инвентарь комплектующих игрока
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mining_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 0,
                is_broken INTEGER DEFAULT 0,
                UNIQUE(user_id, component_id),
                FOREIGN KEY (component_id) REFERENCES mining_components(id)
            )
        ''')

        # Майнинг: риги (собранные установки)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mining_rigs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rig_name TEXT DEFAULT 'Риг',
                gpu_id INTEGER NOT NULL,
                psu_id INTEGER NOT NULL,
                mobo_id INTEGER NOT NULL,
                cooling_id INTEGER DEFAULT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')

        # Майнинг: состояние игрока
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mining_state (
                user_id INTEGER PRIMARY KEY,
                ezhcoins REAL DEFAULT 0,
                is_mining INTEGER DEFAULT 0,
                total_mined REAL DEFAULT 0,
                last_mine TEXT DEFAULT NULL
            )
        ''')
        
        # Банк: вклады
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bank_deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                deposit_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                accrued INTEGER DEFAULT 0,
                opened_at TEXT NOT NULL,
                unlock_at TEXT DEFAULT NULL,
                is_locked INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        ''')

        # Веб: ключи входа
        await db.execute('''
            CREATE TABLE IF NOT EXISTS web_keys (
                key TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
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
            # v5 Columns
            ("users", "diamonds", "INTEGER DEFAULT 0"),
            ("users", "ban_ads", "INTEGER DEFAULT 0"),
            ("users", "ban_books", "INTEGER DEFAULT 0"),
            ("users", "is_fake_admin", "INTEGER DEFAULT 0"),
            ("users", "alert_sent", "INTEGER DEFAULT 0"),
            # Кузница
            ("forge_items", "smelt_result_id", "INTEGER DEFAULT NULL"),
            ("forge_items", "smelt_result_qty", "INTEGER DEFAULT 1"),
            # Домашнее казино
            ("users", "home_casino", "INTEGER DEFAULT 0"),
            ("users", "home_casino_balance", "INTEGER DEFAULT 0")
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
            ("daily_bonus", "25"),
            ("mining_electricity_rate", "1"),  # 1 Ежидзик за 10W/час
            ("mining_base_coin_rate", "0.5"),  # базовый курс Ежкоина
            ("mining_max_rigs", "5")
        ]
        for key, value in default_settings:
            await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))

        # Каталог комплектующих для майнинга
        mining_components = [
            # Видеокарты (comp_type='gpu', mh_rate, power_w)
            ("GT 710", "gpu", 500, "balance", 1, 30, 0, 0),
            ("GTX 1060", "gpu", 1500, "balance", 4, 120, 0, 0),
            ("RTX 3060", "gpu", 4000, "balance", 12, 170, 0, 0),
            ("RTX 4090", "gpu", 12000, "balance", 40, 450, 0, 0),
            # Блоки питания (comp_type='psu', gpu_slots=сколько карт тянет)
            ("БП 500W", "psu", 300, "balance", 0, 0, 1, 0),
            ("БП 1000W", "psu", 800, "balance", 0, 0, 2, 0),
            ("БП 2000W", "psu", 2000, "balance", 0, 0, 5, 0),
            # Материнские платы (comp_type='mobo', 1 риг = 1 плата)
            ("Плата H110", "mobo", 1000, "balance", 0, 0, 0, 0),
            # Охлаждение (comp_type='cooling', break_reduction=снижение шанса поломки)
            ("Вентилятор 120мм", "cooling", 500, "balance", 0, 0, 0, 0.10),
            ("Водяное охлаждение", "cooling", 2000, "balance", 0, 0, 0, 0.30),
        ]
        for comp in mining_components:
            await db.execute('''
                INSERT OR IGNORE INTO mining_components 
                (name, comp_type, price, currency, mh_rate, power_w, gpu_slots, break_reduction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', comp)
        
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
    # AI Hedgehog chat
    ai_chat = State()

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

# Кузница FSM
class ForgeStates(StatesGroup):
    # Создание предмета кузницы (админ)
    waiting_forge_item_name = State()
    waiting_forge_item_price = State()
    waiting_forge_item_currency = State()
    waiting_forge_item_mine_chance = State()
    waiting_forge_item_mine_time = State()
    waiting_forge_item_auctionable = State()
    waiting_forge_item_smeltable = State()
    waiting_forge_item_smelt_result = State()
    waiting_forge_item_smelt_qty = State()
    # Создание крафта (админ)
    waiting_craft_name = State()
    waiting_craft_result = State()
    waiting_craft_result_qty = State()
    waiting_craft_ingredient = State()
    waiting_craft_ingredient_qty = State()
    # Аукцион: выставление лота
    waiting_auction_price = State()
    waiting_auction_currency = State()
    # Поиск крафтов
    waiting_craft_search = State()

class MiningStates(StatesGroup):
    # Обмен Ежкоинов
    waiting_exchange_amount = State()
    # Покупка комплектующих
    waiting_buy_qty = State()

class BankStates(StatesGroup):
    # Открытие вклада — ввод суммы
    waiting_deposit_amount = State()

class HomeCasinoStates(StatesGroup):
    dice_numbers = State()
    star_game = State()
    custom_bet_amount = State()
    add_balance = State()

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
        [KeyboardButton(text="🎰 Ежино")]
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
    # Обновленный дизайн для v5
    buttons = [
        [
            InlineKeyboardButton(text="🦔Покормить🦔", callback_data="feed", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text="🦔Погладить🦔", callback_data="pet", style=ButtonStyle.SUCCESS)
        ],
        [
             InlineKeyboardButton(text="💎 Алмазы", callback_data="diamond_menu"),
             InlineKeyboardButton(text="🤔 Поддержка", callback_data="support")
        ],
        [
            InlineKeyboardButton(text="💸 Перевод", callback_data="transfer_menu"),
            InlineKeyboardButton(text="♻️ Обменник", callback_data="exchange")
        ],
        [
            InlineKeyboardButton(text="🌐 Сайт", callback_data="website"),
             InlineKeyboardButton(text="📞 Звонок", callback_data="call"),
             InlineKeyboardButton(text="🧩 Пазл", callback_data="puzzle")
        ],
        [
            InlineKeyboardButton(text="🔑 Ключ входа", callback_data="web_key", style=ButtonStyle.PRIMARY),
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


def puzzle_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="⚒️ Кузница", callback_data="forge", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text="💻 Майнинг", callback_data="mining", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text="🎰 Домашнее казино", callback_data="hc_casino", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text="🧪 Image Test", callback_data="image_test")],
        [InlineKeyboardButton(text="🤖 ИИ-ЕЖ", callback_data="stub_ai")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])


def forge_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤛 Крафты", callback_data="forge_crafts"),
         InlineKeyboardButton(text="⛏️ Шахты", callback_data="forge_mine")],
        [InlineKeyboardButton(text="📈 Аукцион", callback_data="forge_auction"),
         InlineKeyboardButton(text="✌️ Инвентарь", callback_data="forge_inventory")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="puzzle")]
    ])


def forge_crafts_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Все крафты", callback_data="crafts_list")],
        [InlineKeyboardButton(text="🔍 Поиск крафта", callback_data="craft_search")],
        [InlineKeyboardButton(text="🔥 Печь (переплавка)", callback_data="forge_furnace", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge")]
    ])


def forge_mine_keyboard(mining: bool = False, cooldown: bool = False):
    if mining:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить добычу", callback_data="forge_mine_check", style=ButtonStyle.SUCCESS)],
            [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge")]
        ])
    elif cooldown:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="😴 Передышка...", callback_data="forge_mine")],
            [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛏️ Копать!", callback_data="mine_start", style=ButtonStyle.SUCCESS)],
            [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge")]
        ])


def forge_auction_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏪 Купить предметы", callback_data="auction_shop")],
        [InlineKeyboardButton(text="📊 Чужие предложения", callback_data="auction_listings")],
        [InlineKeyboardButton(text="💰 Мои лоты", callback_data="auction_my_lots")],
        [InlineKeyboardButton(text="📤 Выставить предмет", callback_data="auction_sell")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge")]
    ])


def auction_currency_keyboard(action_data: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Ежидзики", callback_data=f"{action_data}_balance"),
         InlineKeyboardButton(text="💎 Алмазы", callback_data=f"{action_data}_diamonds")],
        [InlineKeyboardButton(text="🐘 Кожа слона", callback_data=f"{action_data}_skin")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="forge_auction")]
    ])


def mining_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Рынок", callback_data="mining_market", style=ButtonStyle.SUCCESS),
         InlineKeyboardButton(text="🔧 Мой риг", callback_data="mining_rig")],
        [InlineKeyboardButton(text="⚡ Майнинг", callback_data="mining_dashboard", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton(text="💱 Обмен", callback_data="mining_exchange")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="puzzle")]
    ])


# =====================================
# 🏦 КЛАВИАТУРЫ БАНКА
# =====================================

BANK_DEPOSIT_TYPES = {
    "demand": {
        "name": "🐾 До востребования",
        "rate": 0.5,       # %/сут
        "lock_hours": 0,   # бессрочно
        "min_amount": 10,
        "description": "Снятие в любой момент без штрафа"
    },
    "stable": {
        "name": "🦔 Стабильный",
        "rate": 1.2,
        "lock_hours": 24,
        "min_amount": 50,
        "description": "Заморозка 24ч, выше ставка"
    },
    "premium": {
        "name": "🏆 Премиум",
        "rate": 2.0,
        "lock_hours": 72,
        "min_amount": 500,
        "description": "Заморозка 72ч, максимальная ставка"
    }
}
BANK_MAX_DEPOSIT = 100000  # Макс. сумма на одном вкладе
BANK_EARLY_PENALTY = 0.10  # 10% штраф за досрочное снятие
BANK_INTEREST_TAX = 0.05   # 5% налог на процент

def bank_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Открыть вклад", callback_data="bank_open", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="📋 Мои вклады", callback_data="bank_my_deposits")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="bank_info")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="finances")]
    ])

def bank_deposit_type_keyboard():
    buttons = []
    for dtype, info in BANK_DEPOSIT_TYPES.items():
        lock_txt = f" (заморозка {info['lock_hours']}ч)" if info['lock_hours'] > 0 else " (бессрочно)"
        buttons.append([InlineKeyboardButton(
            text=f"{info['name']} — {info['rate']}%/сут{lock_txt}",
            callback_data=f"bank_select_{dtype}"
        )])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="bank")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def bank_deposit_actions_keyboard(deposit_id: int, can_withdraw: bool, is_locked: bool):
    buttons = []
    if can_withdraw:
        buttons.append([InlineKeyboardButton(text="💰 Снять вклад", callback_data=f"bank_withdraw_{deposit_id}", style=ButtonStyle.SUCCESS)])
    elif is_locked:
        buttons.append([InlineKeyboardButton(text=f"⚠️ Снять досрочно (штраф {int(BANK_EARLY_PENALTY*100)}%)", callback_data=f"bank_early_{deposit_id}", style=ButtonStyle.DANGER)])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="bank_my_deposits")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
        [InlineKeyboardButton(text="🏦 Банк", callback_data="bank", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="menu")]
    ])


# =====================================
# 🎰 КЛАВИАТУРЫ ДОМАШНЕГО КАЗИНО
# =====================================

def hc_casino_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 Кубик", callback_data="hc_dice"),
            InlineKeyboardButton(text="🦔 Ежино", callback_data="hc_ejino")
        ],
        [
            InlineKeyboardButton(text="🎰 Слоты", callback_data="hc_slots"),
            InlineKeyboardButton(text="🌟 Звёзды", callback_data="hc_star")
        ],
        [InlineKeyboardButton(text="☠️ ×10", callback_data="hc_x10", style=ButtonStyle.DANGER)],
        [
            InlineKeyboardButton(text="➕ Начислить", callback_data="hc_add", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text="➖ Убрать", callback_data="hc_remove", style=ButtonStyle.DANGER)
        ],
        [InlineKeyboardButton(text="🔄 Сброс баланса", callback_data="hc_reset")],
        [InlineKeyboardButton(text="💰 Продать казино (150 ЕЖ)", callback_data="hc_sell", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="puzzle")]
    ])

def hc_casino_buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Купить за 300 ЕЖ", callback_data="hc_buy", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="puzzle")]
    ])

def hc_bet_keyboard(game_type: str):
    buttons = [
        [
            InlineKeyboardButton(text="10", callback_data=f"hc_bet_{game_type}_10"),
            InlineKeyboardButton(text="50", callback_data=f"hc_bet_{game_type}_50"),
            InlineKeyboardButton(text="100", callback_data=f"hc_bet_{game_type}_100")
        ],
        [
            InlineKeyboardButton(text="250", callback_data=f"hc_bet_{game_type}_250"),
            InlineKeyboardButton(text="500", callback_data=f"hc_bet_{game_type}_500"),
            InlineKeyboardButton(text="1000", callback_data=f"hc_bet_{game_type}_1000")
        ],
        [InlineKeyboardButton(text="🖊 Своя ставка", callback_data=f"hc_bet_{game_type}_custom")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="hc_casino")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def hc_dice_numbers_keyboard(selected: list):
    buttons = []
    for row_start in [1, 4]:
        row = []
        for num in range(row_start, row_start + 3):
            if num in selected:
                row.append(InlineKeyboardButton(text=f"✅ {num}", callback_data=f"hc_dice_num_{num}"))
            else:
                row.append(InlineKeyboardButton(text=str(num), callback_data=f"hc_dice_num_{num}"))
        buttons.append(row)
    if len(selected) == 3:
        buttons.append([InlineKeyboardButton(text="🎲 Бросить кубик!", callback_data="hc_dice_roll")])
    else:
        buttons.append([InlineKeyboardButton(text=f"Выбрано: {len(selected)}/3", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="hc_casino")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def hc_slots_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить!", callback_data="hc_slots_spin")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="hc_casino")]
    ])

def hc_ejino_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦔 Крутить Ежино!", callback_data="hc_ejino_spin")],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="hc_casino")]
    ])

def hc_star_field_keyboard(field: list, revealed: list):
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
                row_buttons.append(InlineKeyboardButton(text="❓", callback_data=f"hc_star_{idx}"))
        buttons.append(row_buttons)
    buttons.append([InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data="hc_star_end"), InlineKeyboardButton(text="❌ Отмена", callback_data="hc_casino")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def hc_x10_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☠️ РИСКНУТЬ!", callback_data="hc_x10_try", style=ButtonStyle.DANGER)],
        [InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="hc_casino")]
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
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_image_test")],
        [InlineKeyboardButton(text="◀️ Назад в пазл", callback_data="puzzle")]
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
# 🛠 АДМИН КЛАВИАТУРЫ (AdminOS v5)
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
        [InlineKeyboardButton(text="⚒️ Кузница (предметы)", callback_data="admin_forge")],
        [InlineKeyboardButton(text="📝 Команды", callback_data="admin_manage_commands")],
        [InlineKeyboardButton(text="➕ Добавить команду", callback_data="admin_add_command", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="🖼 Медиа (/add)", callback_data="admin_manage_media")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])


def admin_forge_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить предмет 2", callback_data="admin_add_forge_item", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text="🗑 Удалить предмет", callback_data="admin_del_forge_item")],
        [InlineKeyboardButton(text="🔧 Управление крафтами", callback_data="admin_crafts")],
        [InlineKeyboardButton(text="📋 Список предметов", callback_data="admin_forge_list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_folder_content")]
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
            except Exception as e:
                print(f"⚠️ safe_edit_text: медиа не отправилось ({e}), fallback на текст")
    
    # Обычное поведение
    try:
        if message.photo or message.video:
             # Если сообщение было медиа, а новое текст - удаляем и шлем новое
            await message.delete()
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        print(f"⚠️ safe_edit_text: edit не удался ({e}), пробуем delete+answer")
        try:
            await message.delete()
        except:
            pass
        try:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e2:
            print(f"❌ safe_edit_text: и answer не удался: {e2}")


async def safe_delete(message: Message):
    try:
        await message.delete()
    except:
        pass


async def stream_text(chat_id: int, full_text: str, chunk_size: int = 25, delay: float = 0.06):
    """Стримит текст через sendMessageDraft. Draft — эфемерное 30-сек превью.
    После завершения отправляет финальное сообщение через sendMessage,
    draft при этом автоматически заменится."""
    draft_id = random.randint(1, 2**31 - 1)
    streaming_ok = False

    try:
        # Показываем "Думает..."
        await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text="")
        await asyncio.sleep(0.3)

        current = ""
        for i in range(0, len(full_text), chunk_size):
            current += full_text[i:i + chunk_size]
            try:
                await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text=current)
            except Exception:
                break
            await asyncio.sleep(delay)

        streaming_ok = True
    except Exception:
        pass

    # Даём клиенту отрендерить последний чанк
    if streaming_ok:
        await asyncio.sleep(0.4)

    return streaming_ok


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
            callback.data in ["death_menu_back"] or 
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
    print(f"🔔 /start от user_id={message.from_user.id}")
    try:
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
                promo_to_activate = args.replace("promo_", "").upper()
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
        
        # Проверка статуса (v5)
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
            import traceback
            traceback.print_exc()
            try:
                await message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
            except Exception as e2:
                print(f"❌ Повторная ошибка меню: {e2}")
            
        if promo_to_activate:
            await process_promocode(message, user_id, promo_to_activate)
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА cmd_start: {e}")
        import traceback
        traceback.print_exc()
        try:
            await message.answer("❌ Произошла ошибка. Попробуйте ещё раз.")
        except:
            pass


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
    print(f"🔔 menu callback от user_id={callback.from_user.id}")
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
    except Exception as e:
        print(f"❌ Ошибка show_menu: {e}")
        try:
            await callback.message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
        except Exception as e2:
            print(f"❌ Повторная ошибка show_menu: {e2}")


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    pass  # middleware auto-answers


# =====================================
# 🪦 МЕНЮ ПОСМЕРТИЯ (v5)
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
        if diff.total_seconds() < 1800: # 30 minutes
            remain = 1800 - int(diff.total_seconds())
            await message.answer(f"⏳ Подожди еще {remain} секунд...")
            return

    amount = random.randint(5, 25)
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
        # Проверяем медиа для экрана menu
        media_info = await get_screen_media("menu")
        if media_info:
            try:
                if media_info['media_type'] == 'photo':
                    await message.answer_photo(media_info['file_id'], caption="Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
                elif media_info['media_type'] == 'video':
                    await message.answer_video(media_info['file_id'], caption="Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
                else:
                    await message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
            except Exception:
                await message.answer("Вот меню бота:", reply_markup=main_menu_keyboard(is_user_admin))
        else:
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
    join_date = datetime.strptime(user['join_date'], "%Y-%m-%d %H:%M:%S") if user['join_date'] else datetime.now()
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


@router.message(F.text == "🧩 Пазл")
async def reply_puzzle(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(bot, message.from_user.id, message=message):
        return
    
    full_text = (
        "🧩 Добро пожаловать в пазл! 🧩\n\n"
        "Здесь вы можете найти всякие интересные вещи, "
        "устаревшие функции, и функции, которые находятся в бете!\n\n"
        "Выбери раздел из кнопок ниже 👇"
    )
    await message.answer(full_text, reply_markup=puzzle_keyboard())


@router.callback_query(F.data == "puzzle")
async def puzzle_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    full_text = (
        "🧩 Добро пожаловать в пазл! 🧩\n\n"
        "Здесь вы можете найти всякие интересные вещи, "
        "устаревшие функции, и функции, которые находятся в бете!\n\n"
        "Выбери раздел из кнопок ниже 👇"
    )
    chat_id = callback.message.chat.id
    await stream_text(chat_id, full_text, chunk_size=20, delay=0.04)
    try:
        await callback.message.answer(full_text, reply_markup=puzzle_keyboard())
    except Exception:
        await safe_edit_text(callback.message, full_text, reply_markup=puzzle_keyboard())


@router.message(F.text == "🛠 Панель")
async def reply_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    if await is_admin(user_id):
        # Реальный админ -> AdminOS
        await message.answer(
            "🔒 **Hedgehog AdminOS v5**\nДоступ разрешен. Загрузка модулей...",
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

@router.callback_query(F.data == "image_test")
async def image_test_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    if not HAS_PILLOW:
        await safe_edit_text(callback.message, "⚠️ Функция недоступна (нет библиотеки Pillow).", reply_markup=back_button("puzzle"))
        return

    await state.set_state(UserStates.image_test_text)
    await callback.message.answer(
        "🧪 Image Test\n\nВведите текст, который нужно нарисовать на картинке:",
        reply_markup=image_test_keyboard()
    )

def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Разбивает текст на строки с переносом по словам и ширине."""
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(' ')
        current_line = ""
        for word in words:
            test_line = (current_line + " " + word) if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > max_width and current_line:
                lines.append(current_line)
                # Если одно слово длиннее max_width — режем посимвольно
                bbox_w = draw.textbbox((0, 0), word, font=font)
                if bbox_w[2] - bbox_w[0] > max_width:
                    current_line = ""
                    for ch in word:
                        tst = current_line + ch
                        bb = draw.textbbox((0, 0), tst, font=font)
                        if bb[2] - bb[0] > max_width and current_line:
                            lines.append(current_line)
                            current_line = ch
                        else:
                            current_line = tst
                else:
                    current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
    return lines


def _draw_decorative_background(image: Image.Image):
    """Рисует декоративный фон с градиентом и узорами."""
    import random
    width, height = image.size
    draw = ImageDraw.Draw(image)

    # Градиент: тёмно-синий → фиолетовый → розовый
    for y in range(height):
        ratio = y / height
        if ratio < 0.5:
            r2 = ratio * 2
            r = int(15 + r2 * 80)
            g = int(10 + r2 * 20)
            b = int(60 + r2 * 100)
        else:
            r2 = (ratio - 0.5) * 2
            r = int(95 + r2 * 120)
            g = int(30 + r2 * 40)
            b = int(160 - r2 * 60)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Полупрозрачные декоративные круги
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    random.seed(42)
    for _ in range(18):
        cx = random.randint(0, width)
        cy = random.randint(0, height)
        rad = random.randint(40, 180)
        alpha = random.randint(10, 35)
        color = random.choice([
            (255, 255, 255, alpha),
            (200, 150, 255, alpha),
            (255, 180, 220, alpha),
            (100, 200, 255, alpha),
        ])
        odraw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=color)
    image.paste(Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB"))

    # Уголковые украшения
    draw = ImageDraw.Draw(image)
    corner_len = 40
    cc = (255, 220, 255)
    for cx, cy, dx, dy in [(20, 20, 1, 1), (width - 21, 20, -1, 1), (20, height - 21, 1, -1), (width - 21, height - 21, -1, -1)]:
        draw.line([(cx, cy), (cx + corner_len * dx, cy)], fill=cc, width=3)
        draw.line([(cx, cy), (cx, cy + corner_len * dy)], fill=cc, width=3)


def _draw_watermark_tile(image: Image.Image):
    """Полупрозрачная плиточная водянка 'Говорящий ёж' по всей картинке с наклоном."""
    import math
    width, height = image.size

    # Загружаем шрифт для водянки
    wm_font = None
    for sf in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf",
    ]:
        try:
            wm_font = ImageFont.truetype(sf, 28)
            break
        except Exception:
            continue
    if wm_font is None:
        wm_font = ImageFont.load_default()

    wm_text = "Говорящий ёж  "

    # Рисуем водянку на RGBA оверлее полным белым, потом понизим альфу
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # Измеряем размер текста
    bbox = odraw.textbbox((0, 0), wm_text, font=wm_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    spacing_x = tw + 60
    spacing_y = th + 80

    # Поворот позиций на -30°
    angle_rad = math.radians(-30)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    for row in range(-30, 40):
        for col in range(-20, 25):
            x = col * spacing_x
            y = row * spacing_y
            rx = x * cos_a - y * sin_a + width / 2
            ry = x * sin_a + y * cos_a + height / 2
            odraw.text((rx, ry), wm_text, fill=(255, 255, 255, 255), font=wm_font)

    # Понижаем альфу всех непрозрачных пикселей до 60 (~23% прозрачности)
    a_ch = overlay.getchannel("A")
    # Создаём lookup table: 0→0, 1..255→60
    lut = [0] + [60] * 255
    a_ch = a_ch.point(lut)
    overlay.putalpha(a_ch)

    # Композитим поверх картинки
    image.paste(Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB"))


def _draw_frame(image: Image.Image):
    """Рисует рамку поверх всего (после водянки)."""
    width, height = image.size
    draw = ImageDraw.Draw(image)

    # Двойная рамка
    draw.rectangle([12, 12, width - 13, height - 13], outline=(255, 255, 255), width=3)
    draw.rectangle([20, 20, width - 21, height - 21], outline=(200, 170, 255), width=1)

    # Уголковые украшения
    corner_len = 45
    cc = (255, 220, 255)
    for cx, cy, dx, dy in [(16, 16, 1, 1), (width - 17, 16, -1, 1), (16, height - 17, 1, -1), (width - 17, height - 17, -1, -1)]:
        draw.line([(cx, cy), (cx + corner_len * dx, cy)], fill=cc, width=3)
        draw.line([(cx, cy), (cx, cy + corner_len * dy)], fill=cc, width=3)


@router.message(UserStates.image_test_text)
async def image_test_generate(message: Message, state: FSMContext):
    if not HAS_PILLOW:
        return
    
    text = message.text
    if not text:
        await message.answer("Отправь текст!")
        return
    
    try:
        width, height = 800, 800
        image = Image.new("RGB", (width, height))

        # Декоративный фон
        _draw_decorative_background(image)

        # Плиточная водянка поверх фона
        _draw_watermark_tile(image)

        draw = ImageDraw.Draw(image)

        # Шрифт с поддержкой кириллицы (DejaVu — ставится через apt в Dockerfile)
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Bold.ttf",
            "/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf",
        ]
        font = None
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, 52)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        # Перенос текста по строкам
        margin = 60
        max_text_width = width - margin * 2
        lines = _wrap_text(draw, text, font, max_text_width)

        # Подсчёт общей высоты блока
        line_spacing = 18
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])
        total_height = sum(line_heights) + line_spacing * (len(lines) - 1)

        # Центрирование по вертикали
        y_start = (height - total_height) / 2

        # Тень → основной текст
        current_y = y_start
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            x = (width - lw) / 2

            # Тень
            draw.text((x + 2, current_y + 2), line, fill=(0, 0, 0, 120), font=font)
            # Основной текст — белый с лёгким свечением
            draw.text((x, current_y), line, fill=(255, 255, 255), font=font)

            current_y += line_heights[i] + line_spacing

        # Рамка поверх всего
        _draw_frame(image)

        bio = io.BytesIO()
        image.save(bio, 'PNG')
        bio.seek(0)
        
        input_file = BufferedInputFile(bio.read(), filename="image_test.png")
        
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
# 🥕 ПОКОРМИТЬ (v5 Diamond Drop)
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
# 🤚 ПОГЛАДИТЬ (v5 Diamond Drop)
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
    join_date = datetime.strptime(user['join_date'], "%Y-%m-%d %H:%M:%S") if user['join_date'] else datetime.now()
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
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
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
    # Draft — эфемерное 30-секундное превью. После завершения ОБЯЗАТЕЛЬНО
    # отправляем sendMessage с полным текстом — draft при этом заменится сам.
    # ВАЖНО: text="" показывает "Думает...", а НЕ очищает draft!
    # Draft пропадёт сам когда придёт финальное сообщение от бота.
    draft_id = random.randint(1, 2**31 - 1)
    chat_id = callback.message.chat.id
    streaming_ok = False

    try:
        # Показываем "Думает..." (пустой текст = placeholder)
        await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text="")
        await asyncio.sleep(0.4)

        # Постепенно добавляем текст крупными чанками
        current = ""
        chunk_size = 30
        for i in range(0, len(full_text), chunk_size):
            current += full_text[i:i + chunk_size]
            try:
                await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text=current)
            except Exception:
                # Rate limit или ошибка — прерываем стриминг
                break
            await asyncio.sleep(0.08)

        streaming_ok = True
    except Exception:
        pass  # Стриминг совсем не завёлся — отправим обычным способом

    # Финальное сообщение — ВСЕГДА отправляем через answer() как НОВОЕ сообщение
    # НЕ редактируем callback.message (это меню!) — иначе ломается стриминг
    # Draft автоматически исчезнет когда придёт это сообщение
    if streaming_ok:
        # Даём клиенту секунду чтобы отрендерить последний чанк
        await asyncio.sleep(0.5)

    try:
        await callback.message.answer(full_text, reply_markup=back_button("menu"))
    except Exception:
        # Если answer не работает, отправляем через bot.send_message
        try:
            await bot.send_message(chat_id=chat_id, text=full_text, reply_markup=back_button("menu"))
        except Exception:
            pass


# =====================================
# 📞 ПОЗВОНИТЬ ЕЖУ
# =====================================

@router.callback_query(F.data == "call")
async def call_hedgehog(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    # Сохраняем пустую историю чата
    await state.update_data(ai_history=[])
    await state.set_state(UserStates.ai_chat)
    
    hedgehog_name = user['hedgehog_name']
    status_emoji = "🟢" if user['status'] == 'alive' else "💀"
    text = (
        f"📞 Звонок ежу {hedgehog_name}! {status_emoji}\n\n"
        f"💬 Напиши сообщение — ёж ответит!\n"
        f"💰 Стоимость: 1 сообщение = {AI_CHAT_COST} Ежидзиков\n"
        f"💵 У тебя: {user['balance']} Ежидзиков\n\n"
        f"❌ Нажми «Завершить звонок» чтобы выйти"
    )
    
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Завершить звонок", callback_data="call_end")]
    ]))


@router.callback_query(F.data == "call_end", UserStates.ai_chat)
async def call_end(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    await safe_edit_text(callback.message, "📞 Звонок завершён 📞\n\n🦔 *фыр-фыр... пока!*", reply_markup=back_button("menu"))


@router.message(UserStates.ai_chat)
async def ai_chat_message(message: Message, state: FSMContext):
    """Обработка сообщения в режиме ИИ-чата с ежом. С инструментами и памятью."""
    user_id = message.from_user.id
    text = message.text
    if not text:
        return
    
    # Проверка баланса
    user = await get_user(user_id)
    if not user:
        await state.clear()
        return
    
    if user['balance'] < AI_CHAT_COST:
        await message.answer(
            f"❌ Недостаточно Ежидзиков!\n\n💰 Нужно: {AI_CHAT_COST}\n💵 У тебя: {user['balance']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Завершить звонок", callback_data="call_end")]
            ])
        )
        return
    
    # Списываем Ежидзики
    await update_balance(user_id, -AI_CHAT_COST)
    
    # Статус «печатает» — отправляем и обновляем в фоне
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    typing_stop = asyncio.Event()
    
    async def typing_loop():
        """Обновляем статус 'печатает' каждые 4 секунды, пока ёж думает."""
        while not typing_stop.is_set():
            try:
                await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
            except Exception:
                pass
            try:
                await asyncio.wait_for(typing_stop.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                continue
    
    typing_task = asyncio.create_task(typing_loop())
    
    # Загружаем историю из FSM
    data = await state.get_data()
    ai_history = data.get("ai_history", [])
    
    # Формируем сообщения для API
    api_messages = [{"role": "system", "content": AI_HEDGEHOG_SYSTEM}]
    
    # Добавляем историю (последние N пар)
    for entry in ai_history[-AI_HISTORY_LIMIT:]:
        api_messages.append({"role": "user", "content": entry["user"]})
        api_messages.append({"role": "assistant", "content": entry["assistant"]})
    
    # Добавляем текущее сообщение
    api_messages.append({"role": "user", "content": text})
    
    # Показываем "Думает..."
    chat_id = message.chat.id
    draft_id = random.randint(1, 2**31 - 1)
    
    try:
        # Цикл обработки: вызов API → tool_calls → выполнение → повторный вызов
        max_iterations = 5
        final_response = None
        api_retries = 3  # Количество попыток при ошибке соединения
        
        for _ in range(max_iterations):
            # Попытки вызова API с ретраями при Connection error
            completion = None
            last_error = None
            for attempt in range(api_retries):
                try:
                    completion = groq_client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=api_messages,
                        tools=AI_TOOLS,
                        temperature=0.6,
                        max_completion_tokens=2048,
                        top_p=0.95,
                        stream=False
                    )
                    break  # Успех — выходим из цикла попыток
                except Exception as api_err:
                    last_error = api_err
                    err_msg = str(api_err).lower()
                    # Повторяем только при ошибках соединения
                    if any(kw in err_msg for kw in ['connection', 'timeout', 'timed out', 'network', 'read error', 'reset', '502', '503', '504']):
                        wait = 1.5 * (attempt + 1)  # 1.5с, 3с, 4.5с
                        print(f"⚠️ Попытка {attempt+1}/{api_retries} ошибка: {api_err}. Жду {wait}с...")
                        await asyncio.sleep(wait)
                        continue
                    else:
                        raise  # Другие ошибки — пробрасываем сразу
            
            if completion is None:
                raise last_error  # Все попытки исчерпаны
            
            choice = completion.choices[0]
            msg = choice.message
            
            # Если модель хочет вызвать инструменты
            if msg.tool_calls:
                # Добавляем сообщение ассистента с tool_calls в историю
                api_messages.append(msg)
                
                # Выполняем каждый инструмент
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = {}
                    
                    try:
                        if tool_call.function.arguments:
                            func_args = json.loads(tool_call.function.arguments)
                    except Exception:
                        pass
                    
                    # Выполняем функцию
                    tool_func = AI_TOOL_FUNCTIONS.get(func_name)
                    if tool_func:
                        try:
                            result = await tool_func(user_id, **func_args)
                        except Exception as e:
                            result = f"Ошибка: {e}"
                    else:
                        result = f"Инструмент {func_name} не найден"
                    
                    # Добавляем результат инструмента в историю
                    api_messages.append({
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tool_call.id
                    })
                
                # Продолжаем цикл — отправляем результаты инструментов обратно
                continue
            
            # Если нет tool_calls — это финальный ответ
            final_response = msg.content or "Фыр-фыр... *свернулся в клубок* 🦔"
            break
        
        if not final_response:
            final_response = "Фыр-фыр... *шуршит иголками* 🦔"
        
        # Убираем <think...</think» блоки (Qwen3 reasoning)
        final_response = re.sub(r'<think[\s\S]*?</think\s*>', '', final_response).strip()
        if not final_response:
            final_response = "Фыр-фыр... 🦔"
        
    except Exception as e:
        print(f"❌ Ошибка Groq API: {e}")
        # Возвращаем Ежидзики при ошибке — игрок не виноват
        await update_balance(user_id, AI_CHAT_COST)
        final_response = "Фыр-фыр... *шуршит иголками* Связь оборвалась! Ежидзики возвращены 💰 Попробуй ещё раз! 📞🦔"
    
    # Останавливаем статус «печатает»
    typing_stop.set()
    typing_task.cancel()
    try:
        await typing_task
    except asyncio.CancelledError:
        pass
    
    # Сохраняем в историю
    ai_history.append({"user": text, "assistant": final_response})
    ai_history = ai_history[-AI_HISTORY_LIMIT:]
    await state.update_data(ai_history=ai_history)
    
    # Стримим ответ ежа
    full_text = f"🦔 {final_response}\n\n💰 -{AI_CHAT_COST} Ежидзиков"
    
    streaming_ok = False
    try:
        await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text="")
        await asyncio.sleep(0.3)
        
        current = ""
        chunk_size = 15
        for i in range(0, len(full_text), chunk_size):
            current += full_text[i:i + chunk_size]
            try:
                await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text=current)
            except Exception:
                break
            await asyncio.sleep(0.05)
        
        streaming_ok = True
    except Exception:
        pass
    
    if streaming_ok:
        await asyncio.sleep(0.4)
    
    # Финальное сообщение
    await message.answer(
        full_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Завершить звонок", callback_data="call_end")]
        ])
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
# 💎 АЛМАЗЫ (v5)
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
    
    commission = max(1, int(amount * 0.05))
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
    from web import PUBLIC_URL
    if PUBLIC_URL:
        text = (
            "🌐 **Официальный сайт Говорящего Ежа**\n\n"
            "На сайте можно посмотреть статистику своего ежа, финансы, вклады и многое другое — в красивом интерфейсе!\n\n"
            "🔑 Сначала получите ключ входа (кнопка ниже), затем введите его на сайте."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть сайт", url=PUBLIC_URL)],
            [InlineKeyboardButton(text="🔑 Получить ключ входа", callback_data="web_key")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
        ])
    else:
        text = (
            "🌐 **Официальный сайт Говорящего Ежа**\n\n"
            "⚠️ Сайт временно недоступен (туннель не подключён)\n\n"
            "Получите ключ входа — когда сайт будет доступен, вы сможете войти."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Получить ключ входа", callback_data="web_key")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
        ])
    await safe_edit_text(callback.message, text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "web_key")
async def web_key_generate(callback: CallbackQuery):
    from web import generate_web_key, PUBLIC_URL
    user_id = callback.from_user.id
    key = await generate_web_key(user_id)
    if PUBLIC_URL:
        text = (
            "🔑 **Ключ входа на сайт**\n\n"
            f"`{key}`\n\n"
            "⏱ Действителен 1 час\n"
            "🔗 Нажмите «Скопировать» ниже, затем вставьте ключ на сайте\n\n"
            "⚠️ Не передавайте ключ другим!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопировать", copy_text=CopyTextButton(text=key))],
            [InlineKeyboardButton(text="🌐 Открыть сайт", url=PUBLIC_URL)],
            [InlineKeyboardButton(text="🔄 Новый ключ", callback_data="web_key")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
        ])
    else:
        text = (
            "🔑 **Ключ входа на сайт**\n\n"
            f"`{key}`\n\n"
            "⏱ Действителен 1 час\n"
            "⚠️ Сайт временно недоступен, но ключ сохранён. Когда сайт заработает — вы сможете войти.\n\n"
            "⚠️ Не передавайте ключ другим!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Скопировать", copy_text=CopyTextButton(text=key))],
            [InlineKeyboardButton(text="🔄 Новый ключ", callback_data="web_key")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
        ])
    await safe_edit_text(callback.message, text, reply_markup=kb, parse_mode="Markdown")

# =====================================
# ⚒️ КУЗНИЦА
# =====================================

# --- Вспомогательные функции ---
async def get_forge_inventory(user_id: int) -> dict:
    """Возвращает dict {item_id: quantity} инвентаря кузницы игрока."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT item_id, quantity FROM forge_inventory WHERE user_id = ? AND quantity > 0",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
    return {row['item_id']: row['quantity'] for row in rows}


async def add_forge_item_to_user(user_id: int, item_id: int, qty: int = 1):
    """Добавляет предмет кузницы в инвентарь игрока."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO forge_inventory (user_id, item_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
        ''', (user_id, item_id, qty, qty))
        await db.commit()


async def remove_forge_item_from_user(user_id: int, item_id: int, qty: int = 1) -> bool:
    """Убирает предмет из инвентаря. Возвращает False если недостаточно."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT quantity FROM forge_inventory WHERE user_id = ? AND item_id = ?",
            (user_id, item_id)
        ) as cursor:
            row = await cursor.fetchone()
        if not row or row['quantity'] < qty:
            return False
        new_qty = row['quantity'] - qty
        if new_qty <= 0:
            await db.execute(
                "DELETE FROM forge_inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
        else:
            await db.execute(
                "UPDATE forge_inventory SET quantity = ? WHERE user_id = ? AND item_id = ?",
                (new_qty, user_id, item_id)
            )
        await db.commit()
    return True


async def get_forge_item_by_id(item_id: int):
    """Получает предмет кузницы по ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM forge_items WHERE id = ?", (item_id,)) as cursor:
            return await cursor.fetchone()


# --- ГЛАВНОЕ МЕНЮ КУЗНИЦЫ ---
@router.callback_query(F.data == "forge")
async def forge_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    await safe_edit_text(
        callback.message,
        "⛏️ **Кузница**\n\nВыбери раздел:",
        reply_markup=forge_keyboard(),
        parse_mode="Markdown"
    )


# --- КРАФТЫ ---
@router.callback_query(F.data == "forge_crafts")
async def forge_crafts_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_text(
        callback.message,
        "🤛 **Крафты**\n\nЗдесь можно создавать предметы из ингредиентов "
        "или переплавлять их в печи.",
        reply_markup=forge_crafts_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "crafts_list")
async def crafts_list(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM crafts ORDER BY id") as cursor:
            crafts = await cursor.fetchall()

    if not crafts:
        await callback.answer("📭 Крафтов пока нет!", show_alert=True)
        return

    text = "📖 **Все крафты:**\n\n"
    buttons = []
    for craft in crafts:
        # Получаем ингредиенты
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT ci.quantity, fi.name FROM craft_ingredients ci "
                "JOIN forge_items fi ON ci.item_id = fi.id WHERE ci.craft_id = ?",
                (craft['id'],)
            ) as cursor:
                ingredients = await cursor.fetchall()
            async with db.execute(
                "SELECT name FROM forge_items WHERE id = ?",
                (craft['result_item_id'],)
            ) as cursor:
                result_item = await cursor.fetchone()

        result_name = result_item['name'] if result_item else "???"
        ing_text = ", ".join(f"{ing['name']} x{ing['quantity']}" for ing in ingredients)
        text += f"🔧 **{craft['name']}** → {result_name} x{craft['result_qty']}\n   Нужно: {ing_text}\n\n"
        buttons.append([InlineKeyboardButton(
            text=f"🔧 {craft['name']} → {result_name} x{craft['result_qty']}",
            callback_data=f"craft_{craft['id']}"
        )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_crafts")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(lambda c: c.data and c.data.startswith("craft_") and c.data[6:].isdigit())
async def craft_detail(callback: CallbackQuery):
    craft_id = int(callback.data[6:])

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM crafts WHERE id = ?", (craft_id,)) as cursor:
            craft = await cursor.fetchone()
        if not craft:
            await callback.answer("❌ Крафт не найден!", show_alert=True)
            return

        async with db.execute(
            "SELECT ci.quantity, fi.name, fi.id FROM craft_ingredients ci "
            "JOIN forge_items fi ON ci.item_id = fi.id WHERE ci.craft_id = ?",
            (craft_id,)
        ) as cursor:
            ingredients = await cursor.fetchall()
        async with db.execute("SELECT name FROM forge_items WHERE id = ?", (craft['result_item_id'],)) as cursor:
            result_item = await cursor.fetchone()

    result_name = result_item['name'] if result_item else "???"
    inv = await get_forge_inventory(callback.from_user.id)

    text = f"🔧 **{craft['name']}**\n\n"
    text += f"Результат: **{result_name}** x{craft['result_qty']}\n\n"
    text += "Ингредиенты:\n"
    can_craft = True
    for ing in ingredients:
        have = inv.get(ing['id'], 0)
        need = ing['quantity']
        status = "✅" if have >= need else "❌"
        text += f"  {status} {ing['name']}: {have}/{need}\n"
        if have < need:
            can_craft = False

    buttons = []
    if can_craft:
        buttons.append([InlineKeyboardButton(
            text="🛠 Скрафтить!", callback_data=f"do_craft_{craft_id}", style=ButtonStyle.SUCCESS
        )])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="crafts_list")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("do_craft_"))
async def do_craft(callback: CallbackQuery):
    craft_id = int(callback.data.replace("do_craft_", ""))
    user_id = callback.from_user.id

    # Вся операция в одной транзакции для защиты от race condition
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM crafts WHERE id = ?", (craft_id,)) as cursor:
            craft = await cursor.fetchone()
        if not craft:
            await callback.answer("❌ Крафт не найден!", show_alert=True)
            return

        async with db.execute(
            "SELECT ci.quantity, ci.item_id FROM craft_ingredients ci WHERE ci.craft_id = ?",
            (craft_id,)
        ) as cursor:
            ingredients = await cursor.fetchall()

        # Проверяем наличие ингредиентов атомарно в той же транзакции
        for ing in ingredients:
            async with db.execute(
                "SELECT quantity FROM forge_inventory WHERE user_id = ? AND item_id = ?",
                (user_id, ing['item_id'])
            ) as cursor:
                row = await cursor.fetchone()
            if not row or row['quantity'] < ing['quantity']:
                await callback.answer("❌ Недостаточно ингредиентов!", show_alert=True)
                return

        # Убираем ингредиенты атомарно
        for ing in ingredients:
            await db.execute('''
                UPDATE forge_inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ? AND quantity >= ?
            ''', (ing['quantity'], user_id, ing['item_id'], ing['quantity']))
            # Проверяем что UPDATE затронул строку
            async with db.execute(
                "SELECT quantity FROM forge_inventory WHERE user_id = ? AND item_id = ?",
                (user_id, ing['item_id'])
            ) as cursor:
                row = await cursor.fetchone()
            if row and row['quantity'] <= 0:
                await db.execute("DELETE FROM forge_inventory WHERE user_id = ? AND item_id = ?", (user_id, ing['item_id']))
            elif not row:
                # Не хватило — откатываем
                await db.rollback()
                await callback.answer("❌ Недостаточно ингредиентов!", show_alert=True)
                return

        # Выдаём результат
        await db.execute('''
            INSERT INTO forge_inventory (user_id, item_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?
        ''', (user_id, craft['result_item_id'], craft['result_qty'], craft['result_qty']))

        async with db.execute("SELECT name FROM forge_items WHERE id = ?", (craft['result_item_id'],)) as cursor:
            result = await cursor.fetchone()

        await db.commit()

    result_name = result['name'] if result else "Предмет"
    await callback.answer(f"✅ Скрафчено: {result_name} x{craft['result_qty']}!", show_alert=True)
    # Обновляем отображение крафта
    await craft_detail(callback)


@router.callback_query(F.data == "craft_search")
async def craft_search_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ForgeStates.waiting_craft_search)
    await safe_edit_text(
        callback.message,
        "🔍 Введи название крафта для поиска:",
        reply_markup=back_button("forge_crafts")
    )


@router.message(ForgeStates.waiting_craft_search)
async def craft_search_process(message: Message, state: FSMContext):
    await state.clear()
    query = message.text.strip().lower()

    # LOWER() в SQLite не работает с кириллицей — фильтруем в Python
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM crafts ORDER BY id") as cursor:
            all_crafts = await cursor.fetchall()
    crafts = [c for c in all_crafts if query in c['name'].lower()]

    if not crafts:
        await message.answer("🔍 Ничего не найдено!", reply_markup=back_button("forge_crafts"))
        return

    text = f"🔍 Результаты поиска «{message.text}»:\n\n"
    buttons = []
    for craft in crafts:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT name FROM forge_items WHERE id = ?", (craft['result_item_id'],)) as cursor:
                result_item = await cursor.fetchone()
        result_name = result_item['name'] if result_item else "???"
        text += f"🔧 **{craft['name']}** → {result_name} x{craft['result_qty']}\n"
        buttons.append([InlineKeyboardButton(
            text=f"🔧 {craft['name']}",
            callback_data=f"craft_{craft['id']}"
        )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_crafts")])
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


# --- ПЕЧЬ (ПЕРЕПЛАВКА) ---
@router.callback_query(F.data == "forge_furnace")
async def forge_furnace_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    inv = await get_forge_inventory(user_id)

    if not inv:
        await callback.answer("📭 У тебя нет предметов для переплавки!", show_alert=True)
        return

    # Получаем предметы, которые можно переплавить
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        smeltable_items = []
        for item_id, qty in inv.items():
            async with db.execute("SELECT * FROM forge_items WHERE id = ? AND smeltable = 1", (item_id,)) as cursor:
                item = await cursor.fetchone()
            if item:
                smeltable_items.append((item, qty))

    if not smeltable_items:
        await callback.answer("🔥 Нет предметов, которые можно переплавить!", show_alert=True)
        return

    text = "🔥 **Печь — Переплавка**\n\nВыбери предмет для переплавки:\n\n"
    buttons = []
    for item, qty in smeltable_items:
        if item['smelt_result_id']:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT name FROM forge_items WHERE id = ?", (item['smelt_result_id'],)) as cursor:
                    result = await cursor.fetchone()
            result_name = result['name'] if result else "???"
            text += f"🔥 {item['name']} (x{qty}) → {result_name} x{item['smelt_result_qty']}\n"
            buttons.append([InlineKeyboardButton(
                text=f"🔥 {item['name']} (x{qty}) → {result_name} x{item['smelt_result_qty']}",
                callback_data=f"smelt_{item['id']}"
            )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_crafts")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("smelt_"))
async def do_smelt(callback: CallbackQuery):
    item_id = int(callback.data.replace("smelt_", ""))
    user_id = callback.from_user.id

    item = await get_forge_item_by_id(item_id)
    if not item or not item['smeltable'] or not item['smelt_result_id']:
        await callback.answer("❌ Нельзя переплавить!", show_alert=True)
        return

    # Убираем 1 шт предмета
    ok = await remove_forge_item_from_user(user_id, item_id, 1)
    if not ok:
        await callback.answer("❌ Недостаточно предметов!", show_alert=True)
        return

    # Выдаём результат
    await add_forge_item_to_user(user_id, item['smelt_result_id'], item['smelt_result_qty'])

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT name FROM forge_items WHERE id = ?", (item['smelt_result_id'],)) as cursor:
            result = await cursor.fetchone()

    result_name = result['name'] if result else "Предмет"
    await callback.answer(f"🔥 Переплавлено! Получено: {result_name} x{item['smelt_result_qty']}", show_alert=True)
    await forge_furnace_menu(callback)


# --- ШАХТЫ ---
@router.callback_query(F.data == "forge_mine")
async def forge_mine_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    now = datetime.now()

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mine_state WHERE user_id = ?", (user_id,)) as cursor:
            mine = await cursor.fetchone()

    if mine and mine['mining_until']:
        mining_until = datetime.strptime(mine['mining_until'], "%Y-%m-%d %H:%M:%S")
        if now < mining_until:
            # Ещё копает
            remaining = int((mining_until - now).total_seconds())
            item = await get_forge_item_by_id(mine['current_item_id'])
            item_name = item['name'] if item else "???"
            text = f"⛏️ **Шахта**\n\n⏳ Копаю: **{item_name}**\nОсталось: {remaining} сек."
            await safe_edit_text(callback.message, text, reply_markup=forge_mine_keyboard(mining=True), parse_mode="Markdown")
            return

    if mine and mine['cooldown_until']:
        cooldown_until = datetime.strptime(mine['cooldown_until'], "%Y-%m-%d %H:%M:%S")
        if now < cooldown_until:
            # На передышке
            remaining = int((cooldown_until - now).total_seconds())
            text = f"⛏️ **Шахта**\n\n😴 Передышка...\nПодожди ещё {remaining} сек."
            await safe_edit_text(callback.message, text, reply_markup=forge_mine_keyboard(cooldown=True), parse_mode="Markdown")
            return

    # Можно копать
    text = "⛏️ **Шахта**\n\nНажми «Копать!» чтобы отправиться в шахту.\nЧем дольше копаешь — тем ценнее находка!"
    await safe_edit_text(callback.message, text, reply_markup=forge_mine_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "mine_start")
async def mine_start(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Проверяем не в процессе ли
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mine_state WHERE user_id = ?", (user_id,)) as cursor:
            mine = await cursor.fetchone()

    now = datetime.now()
    if mine:
        if mine['mining_until']:
            mining_until = datetime.strptime(mine['mining_until'], "%Y-%m-%d %H:%M:%S")
            if now < mining_until:
                await callback.answer("⏳ Ты уже копаешь!", show_alert=True)
                return
        if mine['cooldown_until']:
            cooldown_until = datetime.strptime(mine['cooldown_until'], "%Y-%m-%d %H:%M:%S")
            if now < cooldown_until:
                await callback.answer("😴 Передышка! Подожди.", show_alert=True)
                return

    # Выбираем случайный предмет по шансам
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM forge_items WHERE mine_chance > 0") as cursor:
            mineable = await cursor.fetchall()

    if not mineable:
        await callback.answer("⛏️ В шахте пока ничего нет!", show_alert=True)
        return

    # Взвешенный рандом
    import random
    total_chance = sum(item['mine_chance'] for item in mineable)
    roll = random.uniform(0, total_chance)
    cumulative = 0
    chosen = mineable[0]
    for item in mineable:
        cumulative += item['mine_chance']
        if roll <= cumulative:
            chosen = item
            break

    mine_time = chosen['mine_time'] if chosen['mine_time'] > 0 else 5
    mining_until = now + timedelta(seconds=mine_time)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO mine_state (user_id, mining_until, cooldown_until, current_item_id)
            VALUES (?, ?, NULL, ?)
            ON CONFLICT(user_id) DO UPDATE SET mining_until = ?, cooldown_until = NULL, current_item_id = ?
        ''', (user_id, mining_until.strftime("%Y-%m-%d %H:%M:%S"), chosen['id'],
              mining_until.strftime("%Y-%m-%d %H:%M:%S"), chosen['id']))
        await db.commit()

    text = f"⛏️ **Шахта**\n\n⏳ Копаю: **{chosen['name']}**\nВремя добычи: {mine_time} сек."
    await safe_edit_text(callback.message, text, reply_markup=forge_mine_keyboard(mining=True), parse_mode="Markdown")


@router.callback_query(F.data == "forge_mine_check")
async def forge_mine_check(callback: CallbackQuery):
    """Проверяем — может уже накопали?"""
    user_id = callback.from_user.id
    now = datetime.now()

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mine_state WHERE user_id = ?", (user_id,)) as cursor:
            mine = await cursor.fetchone()

    if not mine or not mine['mining_until']:
        await forge_mine_menu(callback)
        return

    mining_until = datetime.strptime(mine['mining_until'], "%Y-%m-%d %H:%M:%S")

    if now >= mining_until:
        # Накопали! Выдаём предмет
        item = await get_forge_item_by_id(mine['current_item_id'])
        if item:
            await add_forge_item_to_user(user_id, item['id'], 1)

        # Устанавливаем кулдаун
        import random
        cooldown = random.randint(10, 50)
        cooldown_until = now + timedelta(seconds=cooldown)

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute('''
                UPDATE mine_state SET mining_until = NULL, cooldown_until = ?, current_item_id = NULL
                WHERE user_id = ?
            ''', (cooldown_until.strftime("%Y-%m-%d %H:%M:%S"), user_id))
            await db.commit()

        item_name = item['name'] if item else "Предмет"
        text = (f"⛏️ **Шахта**\n\n"
                f"✅ Добыто: **{item_name}** x1!\n\n"
                f"😴 Передышка: {cooldown} сек.")
        await safe_edit_text(callback.message, text, reply_markup=forge_mine_keyboard(cooldown=True), parse_mode="Markdown")
    else:
        remaining = int((mining_until - now).total_seconds())
        item = await get_forge_item_by_id(mine['current_item_id'])
        item_name = item['name'] if item else "???"
        text = f"⛏️ **Шахта**\n\n⏳ Копаю: **{item_name}**\nОсталось: {remaining} сек."
        await safe_edit_text(callback.message, text, reply_markup=forge_mine_keyboard(mining=True), parse_mode="Markdown")


# --- АУКЦИОН ---
@router.callback_query(F.data == "forge_auction")
async def forge_auction_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_text(
        callback.message,
        "📈 **Аукцион**\n\nПокупай и продавай предметы!\n"
        "Можно купить по стандартной цене или найти выгодные предложения от других игроков.",
        reply_markup=forge_auction_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "auction_shop")
async def auction_shop(callback: CallbackQuery):
    """Стандартные предметы, которые можно купить напрямую."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM forge_items WHERE auctionable = 1 ORDER BY default_price ASC") as cursor:
            items = await cursor.fetchall()

    if not items:
        await callback.answer("🏪 Нет предметов для покупки!", show_alert=True)
        return

    text = "🏪 **Купить предметы**\n\nСтандартные цены:\n\n"
    buttons = []
    for item in items:
        curr = CURRENCY_LABELS.get(item['currency'], item['currency'])
        text += f"• {item['name']} — {item['default_price']} {curr}\n"
        buttons.append([InlineKeyboardButton(
            text=f"🛒 {item['name']} — {item['default_price']} {curr}",
            callback_data=f"abuy_{item['id']}"
        )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_auction")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("abuy_"))
async def auction_buy_standard(callback: CallbackQuery):
    """Покупка предмета по стандартной цене."""
    item_id = int(callback.data.replace("abuy_", ""))
    user_id = callback.from_user.id
    item = await get_forge_item_by_id(item_id)

    if not item or not item['auctionable']:
        await callback.answer("❌ Предмет недоступен!", show_alert=True)
        return

    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return

    price = item['default_price']
    currency = item['currency']

    # Проверяем баланс
    if currency == 'balance':
        if user['balance'] < price:
            await callback.answer("❌ Недостаточно ежидзиков!", show_alert=True)
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
            await db.commit()
    elif currency == 'diamonds':
        if user['diamonds'] < price:
            await callback.answer("❌ Недостаточно алмазов!", show_alert=True)
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET diamonds = diamonds - ? WHERE user_id = ?", (price, user_id))
            await db.commit()
    elif currency == 'skin':
        if user['elephant_skin'] < price:
            await callback.answer("❌ Недостаточно Кожи слона!", show_alert=True)
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET elephant_skin = elephant_skin - ? WHERE user_id = ?", (price, user_id))
            await db.commit()
    else:
        await callback.answer("❌ Неподдерживаемая валюта!", show_alert=True)
        return

    await add_forge_item_to_user(user_id, item_id, 1)
    curr_name = CURRENCY_LABELS.get(currency, currency)
    await callback.answer(f"✅ Куплено: {item['name']} за {price} {curr_name}!", show_alert=True)
    await auction_shop(callback)


@router.callback_query(F.data == "auction_listings")
async def auction_listings_menu(callback: CallbackQuery, page: int = 0):
    """Чужие предложения на аукционе."""
    user_id = callback.from_user.id
    per_page = 5

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT al.*, fi.name as item_name FROM auction_listings al
            JOIN forge_items fi ON al.item_id = fi.id
            WHERE al.active = 1 AND al.seller_id != ? AND al.is_standard = 0
            ORDER BY al.created_at DESC
        ''', (user_id,)) as cursor:
            all_listings = await cursor.fetchall()

    if not all_listings:
        await callback.answer("📊 Нет предложений от игроков!", show_alert=True)
        return

    total = len(all_listings)
    start = page * per_page
    end = start + per_page
    page_items = all_listings[start:end]

    text = f"📊 **Чужие предложения** (стр. {page + 1})\n\n"
    buttons = []
    for listing in page_items:
        curr = CURRENCY_LABELS.get(listing['currency'], listing['currency'])
        text += f"• {listing['item_name']} x{listing['quantity']} — {listing['price']} {curr}\n"
        buttons.append([InlineKeyboardButton(
            text=f"💰 {listing['item_name']} x{listing['quantity']} — {listing['price']} {curr}",
            callback_data=f"ablid_{listing['id']}"
        )])

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"alst_{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"alst_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_auction")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("alst_"))
async def auction_listings_page(callback: CallbackQuery):
    page = int(callback.data.replace("alst_", ""))
    await auction_listings_menu(callback, page)


@router.callback_query(F.data.startswith("ablid_"))
async def auction_buy_listing(callback: CallbackQuery):
    """Покупка чужого лота."""
    listing_id = int(callback.data.replace("ablid_", ""))
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT al.*, fi.name as item_name FROM auction_listings al
            JOIN forge_items fi ON al.item_id = fi.id
            WHERE al.id = ? AND al.active = 1
        ''', (listing_id,)) as cursor:
            listing = await cursor.fetchone()

    if not listing:
        await callback.answer("❌ Лот не найден!", show_alert=True)
        return

    if listing['seller_id'] == user_id:
        await callback.answer("❌ Это твой собственный лот!", show_alert=True)
        return

    user = await get_user(user_id)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
        return

    price = listing['price']
    currency = listing['currency']
    curr_name = CURRENCY_LABELS.get(currency, currency)

    # Проверяем баланс
    if currency == 'balance':
        if user['balance'] < price:
            await callback.answer("❌ Недостаточно ежидзиков!", show_alert=True)
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, listing['seller_id']))
            await db.execute("UPDATE auction_listings SET active = 0 WHERE id = ?", (listing_id,))
            await db.commit()
    elif currency == 'diamonds':
        if user['diamonds'] < price:
            await callback.answer("❌ Недостаточно алмазов!", show_alert=True)
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET diamonds = diamonds - ? WHERE user_id = ?", (price, user_id))
            await db.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (price, listing['seller_id']))
            await db.execute("UPDATE auction_listings SET active = 0 WHERE id = ?", (listing_id,))
            await db.commit()
    elif currency == 'skin':
        if user['elephant_skin'] < price:
            await callback.answer("❌ Недостаточно Кожи слона!", show_alert=True)
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET elephant_skin = elephant_skin - ? WHERE user_id = ?", (price, user_id))
            await db.execute("UPDATE users SET elephant_skin = elephant_skin + ? WHERE user_id = ?", (price, listing['seller_id']))
            await db.execute("UPDATE auction_listings SET active = 0 WHERE id = ?", (listing_id,))
            await db.commit()
    else:
        await callback.answer("❌ Неподдерживаемая валюта!", show_alert=True)
        return

    await add_forge_item_to_user(user_id, listing['item_id'], listing['quantity'])
    await callback.answer(f"✅ Куплено: {listing['item_name']} x{listing['quantity']} за {price} {curr_name}!", show_alert=True)
    await auction_listings_menu(callback)


@router.callback_query(F.data == "auction_my_lots")
async def auction_my_lots(callback: CallbackQuery):
    """Мои активные лоты."""
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT al.*, fi.name as item_name FROM auction_listings al
            JOIN forge_items fi ON al.item_id = fi.id
            WHERE al.seller_id = ? AND al.active = 1
            ORDER BY al.created_at DESC
        ''', (user_id,)) as cursor:
            listings = await cursor.fetchall()

    if not listings:
        await callback.answer("💰 У тебя нет активных лотов!", show_alert=True)
        return

    text = "💰 **Мои лоты:**\n\n"
    buttons = []
    for listing in listings:
        curr = CURRENCY_LABELS.get(listing['currency'], listing['currency'])
        text += f"• {listing['item_name']} x{listing['quantity']} — {listing['price']} {curr}\n"
        buttons.append([InlineKeyboardButton(
            text=f"❌ Снять: {listing['item_name']} x{listing['quantity']}",
            callback_data=f"acancel_{listing['id']}",
            style=ButtonStyle.DANGER
        )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_auction")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("acancel_"))
async def auction_cancel_listing(callback: CallbackQuery):
    """Отмена своего лота — возврат предмета."""
    listing_id = int(callback.data.replace("acancel_", ""))
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM auction_listings WHERE id = ? AND seller_id = ? AND active = 1",
            (listing_id, user_id)
        ) as cursor:
            listing = await cursor.fetchone()

    if not listing:
        await callback.answer("❌ Лот не найден!", show_alert=True)
        return

    # Возвращаем предмет
    await add_forge_item_to_user(user_id, listing['item_id'], listing['quantity'])

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE auction_listings SET active = 0 WHERE id = ?", (listing_id,))
        await db.commit()

    await callback.answer("✅ Лот снят, предмет возвращён!", show_alert=True)
    await auction_my_lots(callback)


@router.callback_query(F.data == "auction_sell")
async def auction_sell_start(callback: CallbackQuery, state: FSMContext):
    """Выбор предмета для выставления на аукцион."""
    user_id = callback.from_user.id
    inv = await get_forge_inventory(user_id)

    if not inv:
        await callback.answer("📭 У тебя нет предметов для продажи!", show_alert=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        buttons = []
        for item_id, qty in inv.items():
            async with db.execute("SELECT name FROM forge_items WHERE id = ?", (item_id,)) as cursor:
                item = await cursor.fetchone()
            if item:
                buttons.append([InlineKeyboardButton(
                    text=f"📤 {item['name']} (x{qty})",
                    callback_data=f"asell_{item_id}"
                )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_auction")])
    await safe_edit_text(
        callback.message,
        "📤 **Выставить предмет**\n\nВыбери предмет для продажи:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("asell_"))
async def auction_sell_item(callback: CallbackQuery, state: FSMContext):
    """Выбираем валюту для продажи."""
    item_id = int(callback.data.replace("asell_", ""))
    await state.update_data(sell_item_id=item_id)
    await state.set_state(ForgeStates.waiting_auction_currency)

    await safe_edit_text(
        callback.message,
        "💱 Выбери валюту для продажи:",
        reply_markup=auction_currency_keyboard("asellcurr")
    )


@router.callback_query(F.data.startswith("asellcurr_"), ForgeStates.waiting_auction_currency)
async def auction_sell_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.replace("asellcurr_", "")
    data = await state.get_data()
    await state.update_data(sell_currency=currency)
    await state.set_state(ForgeStates.waiting_auction_price)
    await safe_edit_text(
        callback.message,
        "💰 Введи цену за 1 штуку:",
        reply_markup=back_button("forge_auction")
    )


@router.message(ForgeStates.waiting_auction_price)
async def auction_sell_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи положительное число!")
        return

    data = await state.get_data()
    item_id = data.get('sell_item_id')
    currency = data.get('sell_currency', 'balance')
    user_id = message.from_user.id

    # Проверяем наличие
    inv = await get_forge_inventory(user_id)
    qty = inv.get(item_id, 0)
    if qty <= 0:
        await state.clear()
        await message.answer("❌ У тебя нет этого предмета!")
        return

    # Убираем 1 шт из инвентаря
    ok = await remove_forge_item_from_user(user_id, item_id, 1)
    if not ok:
        await state.clear()
        await message.answer("❌ Ошибка!")
        return

    # Создаём лот
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO auction_listings (seller_id, item_id, quantity, price, currency, is_standard, active, created_at)
            VALUES (?, ?, 1, ?, ?, 0, 1, ?)
        ''', (user_id, item_id, price, currency, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()

    await state.clear()
    curr_name = CURRENCY_LABELS.get(currency, currency)
    await message.answer(f"✅ Лот выставлен! 1 предмет за {price} {curr_name}")


# --- ИНВЕНТАРЬ КУЗНИЦЫ ---
@router.callback_query(F.data == "forge_inventory")
async def forge_inventory_menu(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id
    inv = await get_forge_inventory(user_id)

    if not inv:
        await safe_edit_text(
            callback.message,
            "✌️ **Инвентарь кузницы**\n\n📭 Пусто!",
            reply_markup=back_button("forge"),
            parse_mode="Markdown"
        )
        return

    per_page = 8
    items_list = list(inv.items())
    total = len(items_list)
    start = page * per_page
    end = start + per_page
    page_items = items_list[start:end]

    text = f"✌️ **Инвентарь кузницы** (стр. {page + 1})\n\n"
    buttons = []

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        for item_id, qty in page_items:
            async with db.execute("SELECT * FROM forge_items WHERE id = ?", (item_id,)) as cursor:
                item = await cursor.fetchone()
            if item:
                text += f"• **{item['name']}** x{qty}\n"
                buttons.append([InlineKeyboardButton(
                    text=f"📦 {item['name']} x{qty}",
                    callback_data=f"fiitem_{item_id}"
                )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"fipage_{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"fipage_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("fipage_"))
async def forge_inventory_page(callback: CallbackQuery):
    page = int(callback.data.replace("fipage_", ""))
    await forge_inventory_menu(callback, page)


@router.callback_query(F.data.startswith("fiitem_"))
async def forge_inventory_item(callback: CallbackQuery):
    """Подробности предмета из инвентаря кузницы."""
    item_id = int(callback.data.replace("fiitem_", ""))
    user_id = callback.from_user.id
    item = await get_forge_item_by_id(item_id)

    if not item:
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return

    inv = await get_forge_inventory(user_id)
    qty = inv.get(item_id, 0)

    curr = CURRENCY_LABELS.get(item['currency'], item['currency'])
    text = f"📦 **{item['name']}**\n\n"
    text += f"Количество: **{qty}**\n"
    text += f"Стандартная цена: {item['default_price']} {curr}\n"
    if item['mine_chance'] > 0:
        text += f"Шанс в шахте: {item['mine_chance']}%\n"
    if item['smeltable'] and item['smelt_result_id']:
        result = await get_forge_item_by_id(item['smelt_result_id'])
        result_name = result['name'] if result else "???"
        text += f"Переплавка: → {result_name} x{item['smelt_result_qty']}\n"

    buttons = [[InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="forge_inventory")]]
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


# =====================================
# 💻 МАЙНИНГ
# =====================================

# --- Вспомогательные функции ---

async def get_mining_state(user_id: int) -> dict:
    """Получает или создаёт состояние майнинга игрока."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_state WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            await db.execute("INSERT OR IGNORE INTO mining_state (user_id) VALUES (?)", (user_id,))
            await db.commit()
            async with db.execute("SELECT * FROM mining_state WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
    return dict(row) if row else {"user_id": user_id, "ezhcoins": 0, "is_mining": 0, "total_mined": 0, "last_mine": None}


async def get_mining_inventory(user_id: int) -> dict:
    """Возвращает dict {component_id: {quantity, is_broken}} инвентаря майнинга."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT mi.*, mc.name, mc.comp_type FROM mining_inventory mi "
            "JOIN mining_components mc ON mi.component_id = mc.id "
            "WHERE mi.user_id = ? AND mi.quantity > 0",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
    result = {}
    for row in rows:
        result[row['component_id']] = dict(row)
    return result


async def get_user_rigs(user_id: int) -> list:
    """Получает все риги игрока."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_rigs WHERE user_id = ?", (user_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def calc_rig_stats(rig: dict) -> dict:
    """Рассчитывает хешрейт, потребление и защиту рига."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        stats = {"mh": 0, "power": 0, "break_reduction": 0, "gpu_name": "?", "psu_name": "?", "mobo_name": "?"}
        
        async with db.execute("SELECT * FROM mining_components WHERE id = ?", (rig['gpu_id'],)) as cursor:
            gpu = await cursor.fetchone()
        if gpu:
            stats['mh'] += gpu['mh_rate']
            stats['power'] += gpu['power_w']
            stats['gpu_name'] = gpu['name']

        async with db.execute("SELECT * FROM mining_components WHERE id = ?", (rig['psu_id'],)) as cursor:
            psu = await cursor.fetchone()
        if psu:
            stats['psu_name'] = psu['name']

        async with db.execute("SELECT * FROM mining_components WHERE id = ?", (rig['mobo_id'],)) as cursor:
            mobo = await cursor.fetchone()
        if mobo:
            stats['mobo_name'] = mobo['name']

        if rig.get('cooling_id'):
            async with db.execute("SELECT * FROM mining_components WHERE id = ?", (rig['cooling_id'],)) as cursor:
                cool = await cursor.fetchone()
            if cool:
                stats['break_reduction'] = cool['break_reduction']
                stats['cooling_name'] = cool['name']
            else:
                stats['cooling_name'] = None
        else:
            stats['cooling_name'] = None

    return stats


async def get_ezhcoin_rate() -> float:
    """Рассчитывает текущий курс Ежкоина в Ежидзиках."""
    base_rate = float(await get_setting("mining_base_coin_rate", "0.5"))
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COALESCE(SUM(total_mined), 0) FROM mining_state") as cursor:
            total_mined = (await cursor.fetchone())[0]
    # Курс падает по мере накопления Ежкоинов в экономике
    rate = base_rate * 45 / (1 + total_mined / 10000)
    return max(rate, 0.1)  # Минимальный курс


async def ensure_mining_state(user_id: int):
    """Создаёт запись mining_state если её нет."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO mining_state (user_id) VALUES (?)", (user_id,))
        await db.commit()


# --- ГЛАВНОЕ МЕНЮ МАЙНИНГА ---
@router.callback_query(F.data == "mining")
async def mining_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    await ensure_mining_state(callback.from_user.id)
    ms = await get_mining_state(callback.from_user.id)
    rigs = await get_user_rigs(callback.from_user.id)
    rate = await get_ezhcoin_rate()
    
    text = (
        "💻 **Майнинг**\n\n"
        f"💰 Ежкоины: **{ms['ezhcoins']:.2f}**\n"
        f"📊 Курс: 1 Ежкоин = {rate:.2f} Ежидзиков\n"
        f"🔧 Ригов: {len(rigs)}\n"
        f"{'🟢 Майнинг активен' if ms['is_mining'] else '🔴 Майнинг остановлен'}\n\n"
        "Выбери раздел:"
    )
    await safe_edit_text(callback.message, text, reply_markup=mining_keyboard(), parse_mode="Markdown")


# --- РЫНОК КОМПЛЕКТУЮЩИХ ---
@router.callback_query(F.data == "mining_market")
async def mining_market_menu(callback: CallbackQuery):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_components ORDER BY comp_type, price") as cursor:
            components = await cursor.fetchall()

    if not components:
        await callback.answer("🏪 Рынок пуст!", show_alert=True)
        return

    text = "🛒 **Рынок комплектующих**\n\n"
    buttons = []
    type_labels = {"gpu": "🖥 Видеокарты", "psu": "🔌 Блоки питания", "mobo": "🔲 Мат. платы", "cooling": "❄️ Охлаждение"}
    current_type = None
    
    for comp in components:
        if comp['comp_type'] != current_type:
            current_type = comp['comp_type']
            label = type_labels.get(current_type, current_type)
            text += f"\n**{label}:**\n"
        
        curr = CURRENCY_LABELS.get(comp['currency'], comp['currency'])
        info = f"  • {comp['name']} — {comp['price']} {curr}"
        if comp['mh_rate'] > 0:
            info += f" | {comp['mh_rate']} MH/s"
        if comp['power_w'] > 0:
            info += f" | {comp['power_w']}W"
        if comp['gpu_slots'] > 0:
            info += f" | до {comp['gpu_slots']} карт"
        if comp['break_reduction'] > 0:
            info += f" | -{int(comp['break_reduction']*100)}% поломка"
        text += info + "\n"
        
        buttons.append([InlineKeyboardButton(
            text=f"🛒 {comp['name']} — {comp['price']} {curr}",
            callback_data=f"mbuy_{comp['id']}"
        )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="mining")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mbuy_"))
async def mining_buy_component(callback: CallbackQuery):
    """Покупка комплектующего."""
    comp_id = int(callback.data.replace("mbuy_", ""))
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_components WHERE id = ?", (comp_id,)) as cursor:
            comp = await cursor.fetchone()
        if not comp:
            await callback.answer("❌ Товар не найден!", show_alert=True)
            return

        user = await get_user(user_id)
        if not user:
            await callback.answer("❌ Нажми /start!", show_alert=True)
            return

        price = comp['price']
        currency = comp['currency']

        # Проверяем и списываем
        if currency == 'balance':
            if user['balance'] < price:
                await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
                return
            cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (price, user_id, price))
            if cursor.rowcount == 0:
                await callback.answer("❌ Недостаточно Ежидзиков!", show_alert=True)
                return
        elif currency == 'diamonds':
            if user['diamonds'] < price:
                await callback.answer("❌ Недостаточно алмазов!", show_alert=True)
                return
            cursor = await db.execute("UPDATE users SET diamonds = diamonds - ? WHERE user_id = ? AND diamonds >= ?", (price, user_id, price))
            if cursor.rowcount == 0:
                await callback.answer("❌ Недостаточно алмазов!", show_alert=True)
                return
        elif currency == 'skin':
            if user['elephant_skin'] < price:
                await callback.answer("❌ Недостаточно Кожи слона!", show_alert=True)
                return
            cursor = await db.execute("UPDATE users SET elephant_skin = elephant_skin - ? WHERE user_id = ? AND elephant_skin >= ?", (price, user_id, price))
            if cursor.rowcount == 0:
                await callback.answer("❌ Недостаточно Кожи слона!", show_alert=True)
                return
        else:
            await callback.answer("❌ Неподдерживаемая валюта!", show_alert=True)
            return

        # Добавляем в инвентарь
        await db.execute('''
            INSERT INTO mining_inventory (user_id, component_id, quantity, is_broken)
            VALUES (?, ?, 1, 0)
            ON CONFLICT(user_id, component_id) DO UPDATE SET quantity = quantity + 1
        ''', (user_id, comp_id))
        await db.commit()

    curr_name = CURRENCY_LABELS.get(currency, currency)
    await callback.answer(f"✅ Куплено: {comp['name']} за {price} {curr_name}!", show_alert=True)
    await mining_market_menu(callback)


# --- МОЙ РИГ ---
@router.callback_query(F.data == "mining_rig")
async def mining_rig_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    inv = await get_mining_inventory(user_id)
    rigs = await get_user_rigs(user_id)
    max_rigs = int(await get_setting("mining_max_rigs", "5"))

    text = "🔧 **Мои риги**\n\n"
    buttons = []

    if rigs:
        for i, rig in enumerate(rigs):
            stats = await calc_rig_stats(rig)
            status = "🟢" if rig['is_active'] else "🔴"
            cool_text = f"\n   ❄️ {stats.get('cooling_name', 'нет')}" if stats.get('cooling_name') else ""
            text += (
                f"{status} **Риг #{i+1}**\n"
                f"   🖥 {stats['gpu_name']} ({stats['mh']} MH/s)\n"
                f"   🔌 {stats['psu_name']}\n"
                f"   🔲 {stats['mobo_name']}{cool_text}\n\n"
            )
            buttons.append([InlineKeyboardButton(
                text=f"{'🟢' if rig['is_active'] else '🔴'} Риг #{i+1} — {stats['gpu_name']}",
                callback_data=f"mrig_{rig['id']}"
            )])
    else:
        text += "📭 У тебя нет ригов!\n\n"

    # Кнопка сборки если есть компоненты и не достигнут лимит
    has_gpu = any(v['comp_type'] == 'gpu' and v['quantity'] > v.get('is_broken', 0) for v in inv.values())
    has_psu = any(v['comp_type'] == 'psu' and v['quantity'] > v.get('is_broken', 0) for v in inv.values())
    has_mobo = any(v['comp_type'] == 'mobo' and v['quantity'] > v.get('is_broken', 0) for v in inv.values())

    if has_gpu and has_psu and has_mobo and len(rigs) < max_rigs:
        buttons.append([InlineKeyboardButton(text="➕ Собрать риг", callback_data="mrig_build", style=ButtonStyle.SUCCESS)])
    elif len(rigs) >= max_rigs:
        text += f"⚠️ Максимум ригов: {max_rigs}\n"

    buttons.append([InlineKeyboardButton(text="📦 Мои комплектующие", callback_data="mining_parts")])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="mining")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data == "mining_parts")
async def mining_parts_list(callback: CallbackQuery):
    """Показать все комплектующие игрока."""
    user_id = callback.from_user.id
    inv = await get_mining_inventory(user_id)

    if not inv:
        await callback.answer("📦 У тебя нет комплектующих!", show_alert=True)
        return

    type_labels = {"gpu": "🖥 Видеокарты", "psu": "🔌 Блоки питания", "mobo": "🔲 Мат. платы", "cooling": "❄️ Охлаждение"}
    text = "📦 **Мои комплектующие**\n\n"
    buttons = []
    by_type = {}
    for comp_id, item in inv.items():
        t = item['comp_type']
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(item)

    for comp_type, items in by_type.items():
        label = type_labels.get(comp_type, comp_type)
        text += f"**{label}:**\n"
        for item in items:
            broken = " 💥" if item['is_broken'] else ""
            text += f"  • {item['name']} x{item['quantity']}{broken}\n"
            if item['is_broken']:
                # Кнопка починки
                async with aiosqlite.connect(DB_NAME) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute("SELECT price FROM mining_components WHERE id = ?", (item['component_id'],)) as cursor:
                        comp = await cursor.fetchone()
                if comp:
                    repair_cost = comp['price'] // 3
                    buttons.append([InlineKeyboardButton(
                        text=f"🔧 Починить {item['name']} ({repair_cost} Ежидзиков)",
                        callback_data=f"mrepair_{item['component_id']}"
                    )])

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="mining_rig")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mrepair_"))
async def mining_repair(callback: CallbackQuery):
    """Починка сломанного компонента."""
    comp_id = int(callback.data.replace("mrepair_", ""))
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_components WHERE id = ?", (comp_id,)) as cursor:
            comp = await cursor.fetchone()
        if not comp:
            await callback.answer("❌ Компонент не найден!", show_alert=True)
            return

        async with db.execute(
            "SELECT * FROM mining_inventory WHERE user_id = ? AND component_id = ? AND is_broken > 0",
            (user_id, comp_id)
        ) as cursor:
            inv = await cursor.fetchone()
        if not inv:
            await callback.answer("❌ Нечего чинить!", show_alert=True)
            return

        repair_cost = comp['price'] // 3
        cursor = await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (repair_cost, user_id, repair_cost))
        if cursor.rowcount == 0:
            await callback.answer(f"❌ Нужно {repair_cost} Ежидзиков на починку!", show_alert=True)
            return

        await db.execute("UPDATE mining_inventory SET is_broken = is_broken - 1 WHERE user_id = ? AND component_id = ?", (user_id, comp_id))
        await db.commit()

    await callback.answer(f"✅ Починено: {comp['name']} за {repair_cost} Ежидзиков!", show_alert=True)
    await mining_parts_list(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("mrig_") and not c.data.startswith("mrig_build") and c.data[5:].isdigit())
async def mining_rig_detail(callback: CallbackQuery):
    """Детали рига — включить/выключить, удалить."""
    rig_id = int(callback.data.replace("mrig_", ""))
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_rigs WHERE id = ? AND user_id = ?", (rig_id, user_id)) as cursor:
            rig = await cursor.fetchone()
        if not rig:
            await callback.answer("❌ Риг не найден!", show_alert=True)
            return

    rig_dict = dict(rig)
    stats = await calc_rig_stats(rig_dict)
    status = "🟢 Активен" if rig['is_active'] else "🔴 Остановлен"
    
    elec_rate = float(await get_setting("mining_electricity_rate", "1"))
    elec_cost = (stats['power'] / 10) * elec_rate

    text = (
        f"🔧 **Риг #{rig_id}**\n\n"
        f"Статус: {status}\n"
        f"🖥 Видеокарта: {stats['gpu_name']}\n"
        f"🔌 Блок питания: {stats['psu_name']}\n"
        f"🔲 Мат. плата: {stats['mobo_name']}\n"
    )
    if stats.get('cooling_name'):
        text += f"❄️ Охлаждение: {stats['cooling_name']} (-{int(stats['break_reduction']*100)}% поломка)\n"
    text += (
        f"\n📊 Хешрейт: **{stats['mh']} MH/s**\n"
        f"⚡ Потребление: **{stats['power']}W**\n"
        f"💸 Электричество: **{elec_cost:.0f} Ежидзиков/час**\n"
    )

    buttons = []
    if rig['is_active']:
        buttons.append([InlineKeyboardButton(text="⏹ Остановить", callback_data=f"mrigstop_{rig_id}", style=ButtonStyle.DANGER)])
    else:
        buttons.append([InlineKeyboardButton(text="▶️ Запустить", callback_data=f"mrigstart_{rig_id}", style=ButtonStyle.SUCCESS)])
    buttons.append([InlineKeyboardButton(text="🗑 Разобрать риг", callback_data=f"mrigdel_{rig_id}", style=ButtonStyle.DANGER)])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="mining_rig")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mrigstart_"))
async def mining_rig_start(callback: CallbackQuery):
    rig_id = int(callback.data.replace("mrigstart_", ""))
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE mining_rigs SET is_active = 1 WHERE id = ? AND user_id = ?", (rig_id, user_id))
        await db.commit()
    await callback.answer("▶️ Риг запущен!", show_alert=True)
    await mining_rig_detail(callback)


@router.callback_query(F.data.startswith("mrigstop_"))
async def mining_rig_stop(callback: CallbackQuery):
    rig_id = int(callback.data.replace("mrigstop_", ""))
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE mining_rigs SET is_active = 0 WHERE id = ? AND user_id = ?", (rig_id, user_id))
        await db.commit()
    await callback.answer("⏹ Риг остановлен!", show_alert=True)
    await mining_rig_detail(callback)


@router.callback_query(F.data.startswith("mrigdel_"))
async def mining_rig_delete(callback: CallbackQuery):
    """Разобрать риг — компоненты возвращаются в инвентарь."""
    rig_id = int(callback.data.replace("mrigdel_", ""))
    user_id = callback.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mining_rigs WHERE id = ? AND user_id = ?", (rig_id, user_id)) as cursor:
            rig = await cursor.fetchone()
        if not rig:
            await callback.answer("❌ Риг не найден!", show_alert=True)
            return

        # Возвращаем компоненты в инвентарь
        for comp_id in [rig['gpu_id'], rig['psu_id'], rig['mobo_id']]:
            if comp_id:
                await db.execute('''
                    INSERT INTO mining_inventory (user_id, component_id, quantity, is_broken)
                    VALUES (?, ?, 1, 0)
                    ON CONFLICT(user_id, component_id) DO UPDATE SET quantity = quantity + 1
                ''', (user_id, comp_id))
        if rig['cooling_id']:
            await db.execute('''
                INSERT INTO mining_inventory (user_id, component_id, quantity, is_broken)
                VALUES (?, ?, 1, 0)
                ON CONFLICT(user_id, component_id) DO UPDATE SET quantity = quantity + 1
            ''', (user_id, rig['cooling_id']))

        await db.execute("DELETE FROM mining_rigs WHERE id = ?", (rig_id,))
        await db.commit()

    await callback.answer("🗑 Риг разобран, компоненты возвращены!", show_alert=True)
    await mining_rig_menu(callback, None)


@router.callback_query(F.data == "mrig_build")
async def mining_rig_build_start(callback: CallbackQuery, state: FSMContext):
    """Начало сборки рига — выбор видеокарты."""
    user_id = callback.from_user.id
    inv = await get_mining_inventory(user_id)

    gpus = [(k, v) for k, v in inv.items() if v['comp_type'] == 'gpu' and v['quantity'] > v.get('is_broken', 0)]
    if not gpus:
        await callback.answer("❌ Нет видеокарт! Купи на рынке.", show_alert=True)
        return

    text = "🖥 **Сборка рига — Шаг 1/4**\n\nВыбери видеокарту:"
    buttons = []
    for comp_id, item in gpus:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT mh_rate FROM mining_components WHERE id = ?", (comp_id,)) as cursor:
                comp = await cursor.fetchone()
        mh = comp['mh_rate'] if comp else 0
        buttons.append([InlineKeyboardButton(
            text=f"🖥 {item['name']} ({mh} MH/s)",
            callback_data=f"mbuild_gpu_{comp_id}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="mining_rig")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mbuild_gpu_"))
async def mining_rig_build_psu(callback: CallbackQuery, state: FSMContext):
    gpu_id = int(callback.data.replace("mbuild_gpu_", ""))
    await state.update_data(build_gpu=gpu_id)
    
    user_id = callback.from_user.id
    inv = await get_mining_inventory(user_id)
    psus = [(k, v) for k, v in inv.items() if v['comp_type'] == 'psu' and v['quantity'] > v.get('is_broken', 0)]
    if not psus:
        await callback.answer("❌ Нет блоков питания! Купи на рынке.", show_alert=True)
        return

    text = "🔌 **Сборка рига — Шаг 2/4**\n\nВыбери блок питания:"
    buttons = []
    for comp_id, item in psus:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT gpu_slots FROM mining_components WHERE id = ?", (comp_id,)) as cursor:
                comp = await cursor.fetchone()
        slots = comp['gpu_slots'] if comp else 0
        buttons.append([InlineKeyboardButton(
            text=f"🔌 {item['name']} (до {slots} карт)",
            callback_data=f"mbuild_psu_{comp_id}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="mining_rig")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mbuild_psu_"))
async def mining_rig_build_mobo(callback: CallbackQuery, state: FSMContext):
    psu_id = int(callback.data.replace("mbuild_psu_", ""))
    await state.update_data(build_psu=psu_id)
    
    user_id = callback.from_user.id
    inv = await get_mining_inventory(user_id)
    mobos = [(k, v) for k, v in inv.items() if v['comp_type'] == 'mobo' and v['quantity'] > v.get('is_broken', 0)]
    if not mobos:
        await callback.answer("❌ Нет мат. плат! Купи на рынке.", show_alert=True)
        return

    text = "🔲 **Сборка рига — Шаг 3/4**\n\nВыбери материнскую плату:"
    buttons = []
    for comp_id, item in mobos:
        buttons.append([InlineKeyboardButton(
            text=f"🔲 {item['name']}",
            callback_data=f"mbuild_mobo_{comp_id}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="mining_rig")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mbuild_mobo_"))
async def mining_rig_build_cooling(callback: CallbackQuery, state: FSMContext):
    mobo_id = int(callback.data.replace("mbuild_mobo_", ""))
    await state.update_data(build_mobo=mobo_id)
    
    user_id = callback.from_user.id
    inv = await get_mining_inventory(user_id)
    coolings = [(k, v) for k, v in inv.items() if v['comp_type'] == 'cooling' and v['quantity'] > v.get('is_broken', 0)]

    text = "❄️ **Сборка рига — Шаг 4/4**\n\nВыбери охлаждение (или пропусти):"
    buttons = []
    for comp_id, item in coolings:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT break_reduction FROM mining_components WHERE id = ?", (comp_id,)) as cursor:
                comp = await cursor.fetchone()
        br = int((comp['break_reduction'] if comp else 0) * 100)
        buttons.append([InlineKeyboardButton(
            text=f"❄️ {item['name']} (-{br}% поломка)",
            callback_data=f"mbuild_cool_{comp_id}"
        )])
    buttons.append([InlineKeyboardButton(text="⏭ Без охлаждения", callback_data="mbuild_cool_0")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="mining_rig")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mbuild_cool_"))
async def mining_rig_build_finish(callback: CallbackQuery, state: FSMContext):
    """Финальный шаг сборки — создаём риг."""
    cooling_id = int(callback.data.replace("mbuild_cool_", ""))
    if cooling_id == 0:
        cooling_id = None
    
    data = await state.get_data()
    await state.clear()
    gpu_id = data.get('build_gpu')
    psu_id = data.get('build_psu')
    mobo_id = data.get('build_mobo')
    user_id = callback.from_user.id

    if not gpu_id or not psu_id or not mobo_id:
        await callback.answer("❌ Ошибка сборки!", show_alert=True)
        return

    # Всё в одной транзакции — списываем компоненты и создаём риг
    async with aiosqlite.connect(DB_NAME) as db:
        # Списываем GPU
        cursor = await db.execute(
            "UPDATE mining_inventory SET quantity = quantity - 1 WHERE user_id = ? AND component_id = ? AND quantity > 0",
            (user_id, gpu_id)
        )
        if cursor.rowcount == 0:
            await callback.answer("❌ Видеокарта недоступна!", show_alert=True)
            return
        # Списываем PSU
        cursor = await db.execute(
            "UPDATE mining_inventory SET quantity = quantity - 1 WHERE user_id = ? AND component_id = ? AND quantity > 0",
            (user_id, psu_id)
        )
        if cursor.rowcount == 0:
            await db.rollback()
            await callback.answer("❌ Блок питания недоступен!", show_alert=True)
            return
        # Списываем Motherboard
        cursor = await db.execute(
            "UPDATE mining_inventory SET quantity = quantity - 1 WHERE user_id = ? AND component_id = ? AND quantity > 0",
            (user_id, mobo_id)
        )
        if cursor.rowcount == 0:
            await db.rollback()
            await callback.answer("❌ Мат. плата недоступна!", show_alert=True)
            return
        # Списываем Cooling (если есть)
        if cooling_id:
            cursor = await db.execute(
                "UPDATE mining_inventory SET quantity = quantity - 1 WHERE user_id = ? AND component_id = ? AND quantity > 0",
                (user_id, cooling_id)
            )
            if cursor.rowcount == 0:
                await db.rollback()
                await callback.answer("❌ Охлаждение недоступно!", show_alert=True)
                return

        # Проверяем лимит ригов
        max_rigs = int(await get_setting("mining_max_rigs", "5"))
        async with db.execute("SELECT COUNT(*) FROM mining_rigs WHERE user_id = ?", (user_id,)) as cursor:
            rig_count = (await cursor.fetchone())[0]
        if rig_count >= max_rigs:
            await db.rollback()
            await callback.answer(f"❌ Максимум ригов: {max_rigs}!", show_alert=True)
            return

        # Создаём риг
        await db.execute('''
            INSERT INTO mining_rigs (user_id, gpu_id, psu_id, mobo_id, cooling_id, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
        ''', (user_id, gpu_id, psu_id, mobo_id, cooling_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Чистим нулевые количества
        await db.execute("DELETE FROM mining_inventory WHERE quantity <= 0")
        await db.commit()

    await callback.answer("✅ Риг собран! Запусти его в меню ригов.", show_alert=True)
    await mining_rig_menu(callback, None)


# --- ДАШБОРД МАЙНИНГА ---
@router.callback_query(F.data == "mining_dashboard")
async def mining_dashboard(callback: CallbackQuery):
    user_id = callback.from_user.id
    await ensure_mining_state(user_id)
    ms = await get_mining_state(user_id)
    rigs = await get_user_rigs(user_id)
    active_rigs = [r for r in rigs if r['is_active']]

    total_mh = 0
    total_power = 0
    total_break_reduction = 0
    for rig in active_rigs:
        stats = await calc_rig_stats(rig)
        total_mh += stats['mh']
        total_power += stats['power']
        total_break_reduction = max(total_break_reduction, stats['break_reduction'])

    elec_rate = float(await get_setting("mining_electricity_rate", "1"))
    elec_cost = (total_power / 10) * elec_rate
    rate = await get_ezhcoin_rate()

    # Примерная доходность в час
    coin_per_hour = total_mh * 0.05 * random.uniform(0.8, 1.2) if total_mh > 0 else 0
    income_per_hour = coin_per_hour * rate

    text = (
        "⚡ **Майнинг — Панель управления**\n\n"
        f"💰 Ежкоины: **{ms['ezhcoins']:.2f}**\n"
        f"📊 Всего намайнено: {ms['total_mined']:.2f}\n\n"
        f"🔧 Активных ригов: **{len(active_rigs)}/{len(rigs)}**\n"
        f"📈 Общий хешрейт: **{total_mh} MH/s**\n"
        f"⚡ Потребление: **{total_power}W**\n"
        f"💸 Электричество: **{elec_cost:.0f} Ежидзиков/час**\n\n"
        f"📊 Курс: 1 Ежкоин = {rate:.2f} Ежидзиков\n"
        f"💰 Примерно: ~{coin_per_hour:.2f} Ежкоинов/час\n"
        f"💵 ~{income_per_hour:.1f} Ежидзиков/час\n"
    )

    if ms['is_mining'] and active_rigs:
        text += f"\n🟢 **Майнинг работает!**"
    elif not active_rigs:
        text += f"\n⚠️ Нет активных ригов!"
    else:
        text += f"\n🔴 **Майнинг остановлен**"

    buttons = []
    if active_rigs:
        if ms['is_mining']:
            buttons.append([InlineKeyboardButton(text="⏹ Остановить всё", callback_data="mine_stop_all", style=ButtonStyle.DANGER)])
        else:
            buttons.append([InlineKeyboardButton(text="▶️ Запустить всё", callback_data="mine_start_all", style=ButtonStyle.SUCCESS)])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="mining")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data == "mine_start_all")
async def mining_start_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    await ensure_mining_state(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE mining_rigs SET is_active = 1 WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE mining_state SET is_mining = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
    await callback.answer("▶️ Все риги запущены!", show_alert=False)
    await mining_dashboard(callback)


@router.callback_query(F.data == "mine_stop_all")
async def mining_stop_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE mining_rigs SET is_active = 0 WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE mining_state SET is_mining = 0 WHERE user_id = ?", (user_id,))
        await db.commit()
    await callback.answer("⏹ Все риги остановлены!", show_alert=False)
    await mining_dashboard(callback)


# --- ОБМЕН ЕЖКОИНОВ ---
@router.callback_query(F.data == "mining_exchange")
async def mining_exchange_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    await ensure_mining_state(user_id)
    ms = await get_mining_state(user_id)
    rate = await get_ezhcoin_rate()
    diamond_rate = rate / 135  # 45 Ежидзиков = 1 Кожа, 3 Кожи = 1 Алмаз → 135 Ежидзиков ≈ 1 Алмаз

    text = (
        "💱 **Обмен Ежкоинов**\n\n"
        f"💰 У тебя: **{ms['ezhcoins']:.2f}** Ежкоинов\n\n"
        f"📊 Текущие курсы (с учётом комиссии 10%):\n"
        f"  • 1 Ежкоин → {rate * 0.9:.2f} Ежидзиков\n"
        f"  • 1 Ежкоин → {diamond_rate * 0.9:.4f} Алмазов\n\n"
        f"⚠️ Комиссия 10% при обмене"
    )

    buttons = []
    if ms['ezhcoins'] >= 1:
        buttons.append([InlineKeyboardButton(
            text=f"💰 Обменять на Ежидзики",
            callback_data="mex_balance"
        )])
        buttons.append([InlineKeyboardButton(
            text=f"💎 Обменять на Алмазы",
            callback_data="mex_diamonds"
        )])
    else:
        text += "\n\n📭 Недостаточно Ежкоинов (минимум 1)"

    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="mining")])
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("mex_"))
async def mining_exchange_action(callback: CallbackQuery, state: FSMContext):
    """Начало обмена — запрос количества."""
    currency = callback.data.replace("mex_", "")
    await state.update_data(exchange_currency=currency)
    await state.set_state(MiningStates.waiting_exchange_amount)
    
    curr_label = "Ежидзики" if currency == "balance" else "Алмазы"
    await safe_edit_text(
        callback.message,
        f"💱 **Обмен на {curr_label}**\n\nВведи количество Ежкоинов для обмена:",
        reply_markup=back_button("mining_exchange"),
        parse_mode="Markdown"
    )


@router.message(MiningStates.waiting_exchange_amount)
async def mining_exchange_process(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи положительное число!")
        return

    data = await state.get_data()
    await state.clear()
    currency = data.get('exchange_currency', 'balance')
    user_id = message.from_user.id

    ms = await get_mining_state(user_id)
    if ms['ezhcoins'] < amount:
        await message.answer(f"❌ У тебя только {ms['ezhcoins']:.2f} Ежкоинов!")
        return

    rate = await get_ezhcoin_rate()
    commission = amount * 0.10
    net = amount - commission

    if currency == 'balance':
        reward = round(net * rate)
        if reward <= 0:
            await message.answer("❌ Слишком маленькая сумма!")
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE mining_state SET ezhcoins = ezhcoins - ?, total_mined = total_mined WHERE user_id = ?", (amount, user_id))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
            await db.commit()
        await message.answer(f"✅ Обменяно {amount:.2f} Ежкоинов → {reward} Ежидзиков👍\n📉 Комиссия: {commission:.2f}")
    elif currency == 'diamonds':
        diamond_rate = rate / 135
        reward = round(net * diamond_rate)
        if reward <= 0:
            await message.answer("❌ Слишком маленькая сумма для алмазов!")
            return
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE mining_state SET ezhcoins = ezhcoins - ?, total_mined = total_mined WHERE user_id = ?", (amount, user_id))
            await db.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (reward, user_id))
            await db.commit()
        await message.answer(f"✅ Обменяно {amount:.2f} Ежкоинов → {reward} 💎 Алмазов\n📉 Комиссия: {commission:.2f}")


# --- STUB: ИИ-ЕЖ ---
@router.callback_query(F.data == "stub_ai")
async def stub_ai_handler(callback: CallbackQuery):
    await callback.answer("🚧 ИИ-ЕЖ в разработке!\nСледите за новостями.", show_alert=True)

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
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
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
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
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
    chat_id = callback.message.chat.id
    
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
    
    # Стриминг — ЕЖИНО «крутится»
    spin_text = "🦔 ЕЖИНО крутится... 🎰\n\n"
    await stream_text(chat_id, spin_text, chunk_size=15, delay=0.04)
    
    await asyncio.sleep(0.5)
    
    result_text = (
        f"🦔 ЕЖИНО — результат!\n\n"
        f"Результат: ×{multiplier} {emoji}\n\n"
        f"Ставка: {bet} → Выигрыш: {win} Ежидзиков👍"
    )
    try:
        await callback.message.answer(result_text, reply_markup=back_button("casino"))
    except Exception:
        await safe_edit_text(callback.message, result_text, reply_markup=back_button("casino"))


# 🎰 СЛОТЫ
@router.callback_query(F.data == "casino_slots")
async def casino_slots(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
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
    chat_id = callback.message.chat.id
    
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
    
    # Стриминг слотов — символы «выпадают» по одному
    slots_text = f"🎰 Крутим...\n\n"
    await stream_text(chat_id, slots_text, chunk_size=20, delay=0.04)
    
    # Каждый слот «выпадает» с паузой
    for i in range(3):
        partial = " | ".join(result[:i+1])
        remaining = " ❓ " * (2 - i)
        line = f"[ {partial} {remaining}]"
        draft_id = random.randint(1, 2**31 - 1)
        try:
            await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text=f"🎰 Крутим...\n\n{line}")
            await asyncio.sleep(0.6)
        except Exception:
            break
    
    await asyncio.sleep(0.3)
    
    final_text = (
        f"🎰 Результат!\n\n"
        f"[ {result[0]} | {result[1]} | {result[2]} ]\n\n"
        f"Множитель: ×{multiplier} {emoji}\n"
        f"💰 Результат: {win} Ежидзиков👍"
    )
    try:
        await callback.message.answer(final_text, reply_markup=back_button("casino"))
    except Exception:
        await safe_edit_text(callback.message, final_text, reply_markup=back_button("casino"))


# 🌟 НАЙДИ ЗВЕЗДУ (Updated v5 Logic)
@router.callback_query(F.data == "casino_star")
async def casino_star(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
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
        win = 0 # Loss in v5
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


# ☠️ ×10 ОТ СТАВКИ
@router.callback_query(F.data == "casino_x10")
async def casino_x10(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
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
    chat_id = callback.message.chat.id
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
        
        # Драматический стриминг — ×10 ВЫИГРЫШ
        await stream_text(chat_id, "☠️ ×10 ... ", chunk_size=4, delay=0.1)
        await asyncio.sleep(0.8)
        
        result_text = (
            f"☠️ НЕВЕРОЯТНО! 🔥🎉🔥\n\n"
            f"ТЫ ВЫИГРАЛ ×10!!!\n"
            f"💰 +{win} Ежидзиков👍!"
        )
        try:
            await callback.message.answer(result_text, reply_markup=back_button("casino"))
        except Exception:
            await safe_edit_text(callback.message, result_text, reply_markup=back_button("casino"))
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
        
        # Драматический стриминг — проигрыш
        await stream_text(chat_id, "☠️ ×10 ... ", chunk_size=4, delay=0.1)
        await asyncio.sleep(0.5)
        
        result_text = f"☠️ Не повезло... 💀\n\n💸 -{bet} Ежидзиков👍"
        try:
            await callback.message.answer(result_text, reply_markup=back_button("casino"))
        except Exception:
            await safe_edit_text(callback.message, result_text, reply_markup=back_button("casino"))

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
    
    # Стриминг — бонус «раскрывается»
    chat_id = callback.message.chat.id
    await stream_text(chat_id, "🎁 Открываем бонус...", chunk_size=5, delay=0.08)
    
    result_text = (
        f"🎁 Ежедневный бонус получен!\n\n"
        f"+{bonus_amount} Ежидзиков👍\n\n"
        "Приходи завтра за новым бонусом!"
    )
    try:
        await callback.message.answer(result_text, reply_markup=back_button("bonuses"))
    except Exception:
        await safe_edit_text(callback.message, result_text, reply_markup=back_button("bonuses"))


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
# 📚 БИБЛИОТЕКА (v5)
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
        if price <= 0: raise ValueError
    except:
        await message.answer("❌ Введите положительное число (минимум 1)!")
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
    
    bot_username = await _get_bot_username()
    text = (
        "ℹ️ **Информация об Inline режиме**\n\n"
        "Вы можете делиться промокодами через inline-режим бота!\n\n"
        f"1. Введите в любом чате: `@{bot_username} pr CODE`\n"
        "(где CODE — код промокода)\n"
        "2. Появится кнопка **👍 Нажми СЮДА!**\n"
        "3. Отправьте сообщение, и любой пользователь сможет активировать промокод, нажав **🔥 Забрать**.\n\n"
        "💡 Также можно просто ввести `@{bot_username}` — появится подсказка."
    )
    await safe_edit_text(callback.message, text, reply_markup=back_button("support"))


@router.callback_query(F.data == "policy_usage")
async def policy_usage(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    chat_id = callback.message.chat.id
    full_text = (
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
        "🦔 Приятной игры!"
    )
    await stream_text(chat_id, full_text, chunk_size=20, delay=0.04)
    try:
        await callback.message.answer(full_text, reply_markup=back_button("support"))
    except Exception:
        await safe_edit_text(callback.message, full_text, reply_markup=back_button("support"))


@router.callback_query(F.data == "policy_privacy")
async def policy_privacy(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    chat_id = callback.message.chat.id
    full_text = (
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
        "🦔 Ваша безопасность важна для нас!"
    )
    await stream_text(chat_id, full_text, chunk_size=20, delay=0.04)
    try:
        await callback.message.answer(full_text, reply_markup=back_button("support"))
    except Exception:
        await safe_edit_text(callback.message, full_text, reply_markup=back_button("support"))


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
# Админ-панель (AdminOS v5)

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
    await callback.message.answer("💰 Введите сумму изменения (+/-):")

@router.callback_query(F.data.startswith("act_ban_"))
async def act_ban(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.replace("act_ban_", ""))
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_ban_reason)
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
# ⚒️ АДМИНКА: КУЗНИЦА
# =====================================

@router.callback_query(F.data == "admin_forge")
async def admin_forge_menu(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    await safe_edit_text(callback.message, "⚒️ **Кузница — Управление**", reply_markup=admin_forge_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "admin_forge_list")
async def admin_forge_list(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM forge_items ORDER BY id") as cursor:
            items = await cursor.fetchall()

    if not items:
        await callback.answer("📭 Нет предметов кузницы!", show_alert=True)
        return

    text = "📋 **Предметы кузницы:**\n\n"
    for item in items:
        flags = []
        if item['auctionable']:
            flags.append("🏪Аукцион")
        if item['smeltable']:
            flags.append("🔥Переплавка")
        if item['mine_chance'] > 0:
            flags.append(f"⛏️Шахта({item['mine_chance']}%)")
        flag_str = " | ".join(flags) if flags else "—"
        curr = CURRENCY_LABELS.get(item['currency'], item['currency'])
        text += f"#{item['id']} **{item['name']}** — {item['default_price']} {curr}\n  {flag_str}\n\n"

    await safe_edit_text(callback.message, text, reply_markup=back_button("admin_forge"), parse_mode="Markdown")


# --- ДОБАВЛЕНИЕ ПРЕДМЕТА КУЗНИЦЫ (пошаговый FSM) ---
@router.callback_query(F.data == "admin_add_forge_item")
async def admin_add_forge_item_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.set_state(ForgeStates.waiting_forge_item_name)
    await safe_edit_text(callback.message, "➕ Введи название нового предмета кузницы:", reply_markup=back_button("admin_forge"))


@router.message(ForgeStates.waiting_forge_item_name)
async def admin_forge_item_name(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name:
        await message.answer("❌ Введи название!")
        return
    await state.update_data(forge_item_name=name)
    await state.set_state(ForgeStates.waiting_forge_item_price)
    await message.answer(f"💰 Введи стандартную цену для «{name}»:", reply_markup=back_button("admin_forge"))


@router.message(ForgeStates.waiting_forge_item_price)
async def admin_forge_item_price(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    try:
        price = int(message.text)
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи неотрицательное число!")
        return
    await state.update_data(forge_item_price=price)
    await state.set_state(ForgeStates.waiting_forge_item_currency)
    await message.answer("💱 Выбери валюту:", reply_markup=auction_currency_keyboard("afcurr"))


@router.callback_query(F.data.startswith("afcurr_"), ForgeStates.waiting_forge_item_currency)
async def admin_forge_item_currency(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    currency = callback.data.replace("afcurr_", "")
    await state.update_data(forge_item_currency=currency)
    await state.set_state(ForgeStates.waiting_forge_item_mine_chance)
    await safe_edit_text(
        callback.message,
        "⛏️ Введи шанс нахождения в шахте (%):\n\n0 = нет в шахте, число > 0 = шанс.\n"
        "Шансы суммируются (например 2 предмета по 50% = 50/50).",
        reply_markup=back_button("admin_forge")
    )


@router.message(ForgeStates.waiting_forge_item_mine_chance)
async def admin_forge_item_mine_chance(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    try:
        chance = float(message.text)
        if chance < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи число >= 0!")
        return
    await state.update_data(forge_item_mine_chance=chance)
    if chance > 0:
        await state.set_state(ForgeStates.waiting_forge_item_mine_time)
        await message.answer("⏱ Сколько секунд добывается в шахте?", reply_markup=back_button("admin_forge"))
    else:
        # Нет в шахте — пропускаем mine_time
        await state.update_data(forge_item_mine_time=0)
        await state.set_state(ForgeStates.waiting_forge_item_auctionable)
        await message.answer(
            "🏪 Можно ли купить на аукционе по стандартной цене? (да/нет)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="af_yes"),
                 InlineKeyboardButton(text="❌ Нет", callback_data="af_no")]
            ])
        )


@router.message(ForgeStates.waiting_forge_item_mine_time)
async def admin_forge_item_mine_time(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    try:
        mine_time = int(message.text)
        if mine_time < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи положительное число (секунды)!")
        return
    await state.update_data(forge_item_mine_time=mine_time)
    await state.set_state(ForgeStates.waiting_forge_item_auctionable)
    await message.answer(
        "🏪 Можно ли купить на аукционе по стандартной цене? (да/нет)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="af_yes"),
             InlineKeyboardButton(text="❌ Нет", callback_data="af_no")]
        ])
    )


@router.callback_query(F.data.in_(["af_yes", "af_no"]), ForgeStates.waiting_forge_item_auctionable)
async def admin_forge_item_auctionable(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    auctionable = 1 if callback.data == "af_yes" else 0
    await state.update_data(forge_item_auctionable=auctionable)
    await state.set_state(ForgeStates.waiting_forge_item_smeltable)
    await safe_edit_text(
        callback.message,
        "🔥 Можно ли переплавить? (да/нет)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="afs_yes"),
             InlineKeyboardButton(text="❌ Нет", callback_data="afs_no")]
        ])
    )


@router.callback_query(F.data.in_(["afs_yes", "afs_no"]), ForgeStates.waiting_forge_item_smeltable)
async def admin_forge_item_smeltable(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    smeltable = 1 if callback.data == "afs_yes" else 0
    await state.update_data(forge_item_smeltable=smeltable)

    if smeltable:
        # Нужно выбрать во что переплавляется
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, name FROM forge_items ORDER BY id") as cursor:
                items = await cursor.fetchall()

        if not items:
            # Нет предметов для выбора результата переплавки
            await state.update_data(forge_item_smelt_result_id=None, forge_item_smelt_qty=0)
            await _save_forge_item(callback.message, state)
            return

        await state.set_state(ForgeStates.waiting_forge_item_smelt_result)
        buttons = []
        for item in items:
            buttons.append([InlineKeyboardButton(
                text=f"→ {item['name']}",
                callback_data=f"afsr_{item['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_forge")])
        await safe_edit_text(
            callback.message,
            "🔥 Во что переплавляется? Выбери предмет:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await state.update_data(forge_item_smelt_result_id=None, forge_item_smelt_qty=0)
        await _save_forge_item(callback.message, state)


@router.callback_query(F.data.startswith("afsr_"), ForgeStates.waiting_forge_item_smelt_result)
async def admin_forge_item_smelt_result(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    result_id = int(callback.data.replace("afsr_", ""))
    await state.update_data(forge_item_smelt_result_id=result_id)
    await state.set_state(ForgeStates.waiting_forge_item_smelt_qty)
    await safe_edit_text(
        callback.message,
        "🔢 Сколько штук получается при переплавке?",
        reply_markup=back_button("admin_forge")
    )


@router.message(ForgeStates.waiting_forge_item_smelt_qty)
async def admin_forge_item_smelt_qty(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    try:
        qty = int(message.text)
        if qty < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи положительное число!")
        return
    await state.update_data(forge_item_smelt_qty=qty)
    await _save_forge_item(message, state)


async def _save_forge_item(message_or_callback_msg, state: FSMContext):
    """Сохраняет предмет кузницы в БД."""
    data = await state.get_data()
    name = data['forge_item_name']
    price = data['forge_item_price']
    currency = data.get('forge_item_currency', 'balance')
    mine_chance = data.get('forge_item_mine_chance', 0)
    mine_time = data.get('forge_item_mine_time', 0)
    auctionable = data.get('forge_item_auctionable', 0)
    smeltable = data.get('forge_item_smeltable', 0)
    smelt_result_id = data.get('forge_item_smelt_result_id')
    smelt_result_qty = data.get('forge_item_smelt_qty', 0)

    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute('''
                INSERT INTO forge_items (name, default_price, currency, mine_chance, mine_time,
                    auctionable, smeltable, smelt_result_id, smelt_result_qty, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, price, currency, mine_chance, mine_time, auctionable, smeltable,
                  smelt_result_id, smelt_result_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            await db.commit()
            await state.clear()
            await message_or_callback_msg.answer(
                f"✅ Предмет кузницы «{name}» создан!\n"
                f"💰 Цена: {price} {CURRENCY_LABELS.get(currency, currency)}\n"
                f"⛏️ Шахта: {mine_chance}% ({mine_time}с)\n"
                f"🏪 Аукцион: {'Да' if auctionable else 'Нет'}\n"
                f"🔥 Переплавка: {'Да' if smeltable else 'Нет'}",
                reply_markup=admin_forge_keyboard()
            )
        except Exception as e:
            await state.clear()
            await message_or_callback_msg.answer(f"❌ Ошибка: {e}", reply_markup=admin_forge_keyboard())


# --- УДАЛЕНИЕ ПРЕДМЕТА КУЗНИЦЫ ---
@router.callback_query(F.data == "admin_del_forge_item")
async def admin_del_forge_item(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM forge_items ORDER BY id") as cursor:
            items = await cursor.fetchall()

    if not items:
        await callback.answer("📭 Нет предметов!", show_alert=True)
        return

    buttons = []
    for item in items[:20]:
        buttons.append([InlineKeyboardButton(
            text=f"🗑 {item['name']}",
            callback_data=f"delfi_{item['id']}",
            style=ButtonStyle.DANGER
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_forge")])
    await safe_edit_text(callback.message, "🗑 Выбери предмет для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("delfi_"))
async def delete_forge_item(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    item_id = int(callback.data.replace("delfi_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name FROM forge_items WHERE id = ?", (item_id,)) as cursor:
            item = await cursor.fetchone()
        if item:
            await db.execute("DELETE FROM forge_items WHERE id = ?", (item_id,))
            await db.execute("DELETE FROM forge_inventory WHERE item_id = ?", (item_id,))
            await db.execute("DELETE FROM craft_ingredients WHERE item_id = ?", (item_id,))
            await db.execute("DELETE FROM auction_listings WHERE item_id = ?", (item_id,))
            await db.commit()
            await callback.answer(f"✅ «{item[0]}» удалён!", show_alert=True)
    await admin_del_forge_item(callback)


# --- УПРАВЛЕНИЕ КРАФТАМИ ---
@router.callback_query(F.data == "admin_crafts")
async def admin_crafts_menu(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM crafts ORDER BY id") as cursor:
            crafts = await cursor.fetchall()

    buttons = [[InlineKeyboardButton(text="➕ Создать крафт", callback_data="admin_add_craft", style=ButtonStyle.SUCCESS)]]

    if crafts:
        for craft in crafts:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT name FROM forge_items WHERE id = ?", (craft['result_item_id'],)) as cursor:
                    result = await cursor.fetchone()
            result_name = result['name'] if result else "???"
            buttons.append([InlineKeyboardButton(
                text=f"🗑 {craft['name']} → {result_name} x{craft['result_qty']}",
                callback_data=f"delcraft_{craft['id']}",
                style=ButtonStyle.DANGER
            )])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_forge")])
    await safe_edit_text(callback.message, "🔧 **Управление крафтами**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data == "admin_add_craft")
async def admin_add_craft_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name FROM forge_items ORDER BY id") as cursor:
            items = await cursor.fetchall()

    if not items:
        await callback.answer("❌ Сначала создай хотя бы 1 предмет кузницы!", show_alert=True)
        return

    await state.set_state(ForgeStates.waiting_craft_name)
    await safe_edit_text(callback.message, "🔧 Введи название крафта:", reply_markup=back_button("admin_crafts"))


@router.message(ForgeStates.waiting_craft_name)
async def admin_craft_name(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name:
        await message.answer("❌ Введи название!")
        return
    await state.update_data(craft_name=name)

    # Выбираем результат крафта
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name FROM forge_items ORDER BY id") as cursor:
            items = await cursor.fetchall()

    buttons = []
    for item in items:
        buttons.append([InlineKeyboardButton(text=f"→ {item['name']}", callback_data=f"acr_{item['id']}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_crafts")])

    await state.set_state(ForgeStates.waiting_craft_result)
    await message.answer("🎯 Выбери предмет-результат крафта:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("acr_"), ForgeStates.waiting_craft_result)
async def admin_craft_result(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    result_id = int(callback.data.replace("acr_", ""))
    await state.update_data(craft_result_id=result_id)
    await state.set_state(ForgeStates.waiting_craft_result_qty)
    await safe_edit_text(callback.message, "🔢 Сколько штук получается?", reply_markup=back_button("admin_crafts"))


@router.message(ForgeStates.waiting_craft_result_qty)
async def admin_craft_result_qty(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    try:
        qty = int(message.text)
        if qty < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введи положительное число!")
        return
    await state.update_data(craft_result_qty=qty)
    await state.set_state(ForgeStates.waiting_craft_ingredient)
    await message.answer(
        "🧪 Теперь добавим ингредиенты.\n\n"
        "Введи ингредиент в формате: `название количество`\n"
        "Например: `Железо 3`\n\n"
        "Когда закончишь — напиши `готово`",
        reply_markup=back_button("admin_crafts"),
        parse_mode="Markdown"
    )


@router.message(ForgeStates.waiting_craft_ingredient)
async def admin_craft_ingredient(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    text = message.text.strip().lower()

    if text == "готово":
        await _save_craft(message, state)
        return

    # Парсим "название количество"
    parts = message.text.strip().rsplit(" ", 1)
    if len(parts) != 2:
        await message.answer("❌ Формат: `название количество`\nНапример: `Железо 3`", parse_mode="Markdown")
        return

    item_name, qty_str = parts
    try:
        qty = int(qty_str)
        if qty < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Количество должно быть положительным числом!")
        return

    # Ищем предмет (регистронезависимо, LOWER в SQLite не работает с кириллицей)
    item_name_lower = item_name.lower()
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name FROM forge_items") as cursor:
            all_items = await cursor.fetchall()
    item = None
    for fi in all_items:
        if fi['name'].lower() == item_name_lower:
            item = fi
            break

    if not item:
        await message.answer(f"❌ Предмет «{item_name}» не найден! Проверь название.")
        return

    # Добавляем ингредиент в список
    data = await state.get_data()
    ingredients = data.get('craft_ingredients', [])
    ingredients.append({'item_id': item['id'], 'name': item['name'], 'qty': qty})
    await state.update_data(craft_ingredients=ingredients)

    ing_list = ", ".join(f"{ing['name']} x{ing['qty']}" for ing in ingredients)
    await message.answer(
        f"✅ Добавлено: {item['name']} x{qty}\n\n"
        f"Текущие ингредиенты: {ing_list}\n\n"
        f"Добавь ещё или напиши `готово`",
        parse_mode="Markdown"
    )


async def _save_craft(message: Message, state: FSMContext):
    """Сохраняет крафт в БД."""
    data = await state.get_data()
    craft_name = data.get('craft_name', 'Крафт')
    result_id = data.get('craft_result_id')
    result_qty = data.get('craft_result_qty', 1)
    ingredients = data.get('craft_ingredients', [])

    if not result_id:
        await state.clear()
        await message.answer("❌ Ошибка: не выбран результат!")
        return

    if not ingredients:
        await state.clear()
        await message.answer("❌ Нужен хотя бы 1 ингредиент!")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            INSERT INTO crafts (name, result_item_id, result_qty, created_at)
            VALUES (?, ?, ?, ?)
        ''', (craft_name, result_id, result_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        craft_id = cursor.lastrowid

        for ing in ingredients:
            await db.execute('''
                INSERT INTO craft_ingredients (craft_id, item_id, quantity)
                VALUES (?, ?, ?)
            ''', (craft_id, ing['item_id'], ing['qty']))

        await db.commit()

    await state.clear()
    ing_text = ", ".join(f"{ing['name']} x{ing['qty']}" for ing in ingredients)
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT name FROM forge_items WHERE id = ?", (result_id,)) as cursor:
            result = await cursor.fetchone()
    result_name = result['name'] if result else "???"

    await message.answer(
        f"✅ Крафт создан!\n\n"
        f"🔧 **{craft_name}** → {result_name} x{result_qty}\n"
        f"Ингредиенты: {ing_text}",
        reply_markup=admin_forge_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("delcraft_"))
async def delete_craft(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    craft_id = int(callback.data.replace("delcraft_", ""))
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM craft_ingredients WHERE craft_id = ?", (craft_id,))
        await db.execute("DELETE FROM crafts WHERE id = ?", (craft_id,))
        await db.commit()
    await callback.answer("✅ Крафт удалён!", show_alert=True)
    await admin_crafts_menu(callback)


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
# 📚 МОДЕРАЦИЯ КНИГ (v5)
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

# ⚠️ FSM-хэндлеры банка и домашнего казино ДОЛЖНЫ быть раньше catch-all (F.text)
@router.message(BankStates.waiting_deposit_amount)
async def bank_process_deposit(message: Message, state: FSMContext):
    data = await state.get_data()
    dtype = data.get('deposit_type')
    await state.clear()
    
    if not dtype or dtype not in BANK_DEPOSIT_TYPES:
        await message.answer("❌ Ошибка, попробуйте снова.")
        return
    
    info = BANK_DEPOSIT_TYPES[dtype]
    
    # Парсим сумму
    try:
        amount = int(message.text.strip().replace(' ', '').replace(',', ''))
    except ValueError:
        await message.answer("❌ Введите целое число!", reply_markup=back_button("bank_open"))
        return
    
    if amount < info['min_amount']:
        await message.answer(f"❌ Минимальная сумма для этого вклада: {info['min_amount']} ЕЖ", reply_markup=back_button("bank_open"))
        return
    
    if amount > BANK_MAX_DEPOSIT:
        await message.answer(f"❌ Максимальная сумма вклада: {BANK_MAX_DEPOSIT:,} ЕЖ", reply_markup=back_button("bank_open"))
        return
    
    user = await get_user(message.from_user.id)
    if not user or user['balance'] < amount:
        await message.answer("❌ Недостаточно Ежидзиков!", reply_markup=back_button("bank_open"))
        return
    
    # Проверяем что такого типа ещё нет
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id FROM bank_deposits WHERE user_id = ? AND deposit_type = ? AND status = 'active'", (message.from_user.id, dtype)) as cursor:
            existing = await cursor.fetchone()
        if existing:
            await message.answer("❌ У вас уже есть активный вклад этого типа!", reply_markup=back_button("bank"))
            return
        
        # Списываем деньги
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, message.from_user.id))
        
        now = datetime.now()
        unlock_at = None
        is_locked = 0
        if info['lock_hours'] > 0:
            unlock_at = (now + timedelta(hours=info['lock_hours'])).strftime("%Y-%m-%d %H:%M:%S")
            is_locked = 1
        
        await db.execute(
            "INSERT INTO bank_deposits (user_id, deposit_type, amount, accrued, opened_at, unlock_at, is_locked, status) VALUES (?, ?, ?, 0, ?, ?, ?, 'active')",
            (message.from_user.id, dtype, amount, now.strftime("%Y-%m-%d %H:%M:%S"), unlock_at, is_locked)
        )
        await db.commit()
    
    lock_txt = f"\n🔒 Разблокировка: {unlock_at}" if unlock_at else "\n🔓 Снятие в любой момент"
    await message.answer(
        f"✅ Вклад открыт!\n\n"
        f"{info['name']}\n"
        f"💵 Сумма: {amount} ЕЖ\n"
        f"📊 Ставка: {info['rate']}%/сут"
        f"{lock_txt}",
        reply_markup=back_button("bank")
    )


# --- Домашнее казино: FSM обработка ввода ---
@router.message(HomeCasinoStates.custom_bet_amount)
async def hc_process_custom_bet(message: Message, state: FSMContext):
    try:
        bet = int(message.text.strip().replace(' ', '').replace(',', ''))
        if bet <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи положительное число!")
        return
    
    data = await state.get_data()
    game_type = data.get('game_type')
    
    hc_bal = await get_hc_balance(message.from_user.id)
    if hc_bal < bet:
        await message.answer("❌ Недостаточно Ежедзуков!")
        return
    
    await state.update_data(bet=bet)
    
    if game_type == "dice":
        await state.set_state(HomeCasinoStates.dice_numbers)
        await state.update_data(selected_numbers=[])
        await message.answer(f"🎲 Ставка: {bet} Ежедзуков\n\nВыбери 3 числа (1-6):", reply_markup=hc_dice_numbers_keyboard([]))
    elif game_type == "ejino":
        await state.set_state(None)
        await message.answer(f"🦔 ЕЖИНО\n\nСтавка: {bet} Ежедзуков\n\nКрути!", reply_markup=hc_ejino_keyboard())
    elif game_type == "slots":
        await state.set_state(None)
        await message.answer(f"🎰 Слоты\n\nСтавка: {bet} Ежедзуков", reply_markup=hc_slots_keyboard())
    elif game_type == "star":
        field = ["❌"] * 25
        star_positions = random.sample(range(25), 5)
        for pos in star_positions:
            field[pos] = "⭐"
        await state.update_data(field=field, revealed=[], total_win=0)
        await state.set_state(HomeCasinoStates.star_game)
        await message.answer(f"🌟 Найди звезду!\n\nСтавка за нажатие: {bet} Ежедзуков\nВыигрыш: 0\n\nНажимай на ❓!", reply_markup=hc_star_field_keyboard(field, []))
    elif game_type == "x10":
        await state.set_state(None)
        await message.answer(f"☠️ ×10 от ставки!\n\nСтавка: {bet} Ежедзуков\n\nШанс 5%! 💀", reply_markup=hc_x10_keyboard())
    else:
        await state.clear()
        await message.answer("❌ Ошибка, попробуй снова.")


# ⚠️ HomeCasinoStates.add_balance и custom_bet_amount — до catch-all
@router.message(HomeCasinoStates.add_balance)
async def hc_add_process(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get('hc_action', 'add')
    await state.clear()
    
    user = await get_user(message.from_user.id)
    if not user or not user['home_casino']:
        await message.answer("❌ У тебя нет казино!")
        return
    try:
        amount = int(message.text.strip().replace(' ', '').replace(',', ''))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Введи положительное число!", reply_markup=back_button("hc_casino"))
        return
    
    if action == "remove":
        hc_bal = await get_hc_balance(message.from_user.id)
        if amount > hc_bal:
            amount = hc_bal
        await update_hc_balance(message.from_user.id, -amount)
        new_bal = await get_hc_balance(message.from_user.id)
        await message.answer(f"✅ Списано {amount} Ежедзуков!\n💰 Баланс: {new_bal}", reply_markup=back_button("hc_casino"))
    else:
        await update_hc_balance(message.from_user.id, amount)
        new_bal = await get_hc_balance(message.from_user.id)
        await message.answer(f"✅ Начислено {amount} Ежедзуков!\n💰 Баланс: {new_bal}", reply_markup=back_button("hc_casino"))


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

    # Promocodes (тихая проверка — не спамим если текст не промокод)
    await process_promocode(message, user_id, text.upper(), silent_not_found=True)

async def process_promocode(message: Message, user_id: int, code: str, silent_not_found: bool = False):
    """Обрабатывает активацию промокода. Атомарная операция.
    
    Args:
        silent_not_found: если True, не выводить ошибку если промокод не найден
                          (для автоматической проверки текста в чате)
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM used_promocodes WHERE user_id = ? AND code = ?", (user_id, code)) as cursor:
            if await cursor.fetchone():
                await message.answer("❌ Вы уже активировали этот промокод!")
                return
        async with db.execute("SELECT * FROM promocodes WHERE code = ? AND uses_left > 0", (code,)) as cursor:
            promo = await cursor.fetchone()
        if not promo:
            if not silent_not_found:
                await message.answer("❌ Промокод не найден или все активации исчерпаны.")
            return
        
        reward_type = promo['reward_type']
        reward_value = promo['reward_value']
        
        # Все обновления в одной транзакции
        if reward_type == "balance":
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (int(reward_value), user_id))
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

# Кеш username бота (чтобы не дёргать get_me() при каждом inline-запросе)
_bot_username_cache: str | None = None

async def _get_bot_username() -> str:
    global _bot_username_cache
    if _bot_username_cache is None:
        me = await bot.get_me()
        _bot_username_cache = me.username
    return _bot_username_cache


@router.inline_query()
async def inline_query_handler(query: InlineQuery):
    text = query.query.strip()
    results = []
    bot_username = await _get_bot_username()
    
    # Режим "pr CODE"
    if text.lower().startswith("pr "):
        code = text[3:].strip().upper()
        if code:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM promocodes WHERE code = ? AND uses_left > 0", (code,)) as cursor:
                    promo = await cursor.fetchone()
            
            if promo:
                type_names = {"balance": "ежидзиков👍", "ants": "муравьёв🐜", "color": "цвет🎨"}
                curr_name = type_names.get(promo['reward_type'], promo['reward_type'])
                
                description_text = (
                    f"🦔 Промокод в боте Говорящий Еж! 🦔\n"
                    f"⚡ Активаций осталось: {promo['uses_left']}\n"
                    f"🌟 Даёт: {promo['reward_value']} {curr_name}"
                )
                
                # Используем callback-кнопку вместо URL — надёжнее!
                # URL-deeplink часто не срабатывает у уже зарегистрированных пользователей
                callback_code = f"ipromo_{code}"
                # Проверяем длину callback_data (лимит 64 байта)
                if len(callback_code.encode('utf-8')) <= 64:
                    results.append(InlineQueryResultArticle(
                        id=f"promo_{code}",
                        title="👍 Нажми СЮДА!",
                        description=f"Промокод: {code} — {promo['reward_value']} {curr_name}",
                        input_message_content=InputTextMessageContent(message_text=description_text),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔥 Забрать", callback_data=callback_code)]
                        ])
                    ))
                else:
                    # Fallback: слишком длинный код — используем URL
                    url = f"https://t.me/{bot_username}?start=promo_{code}"
                    results.append(InlineQueryResultArticle(
                        id=f"promo_{code}",
                        title="👍 Нажми СЮДА!",
                        description=f"Промокод: {code} — {promo['reward_value']} {curr_name}",
                        input_message_content=InputTextMessageContent(message_text=description_text),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔥 Забрать", url=url)]
                        ])
                    ))
            else:
                # Промокод не найден — показываем сообщение
                results.append(InlineQueryResultArticle(
                    id="not_found",
                    title="❌ Промокод не найден",
                    description=f"Код \"{code}\" не существует или исчерпан",
                    input_message_content=InputTextMessageContent(
                        message_text=f"❌ Промокод \"{code}\" не найден или все активации исчерпаны."
                    )
                ))
    
    # Если пустой запрос
    if not text or not text.lower().startswith("pr "):
        results.append(InlineQueryResultArticle(
            id="info",
            title="🎟 Поделиться промокодом",
            description=f"Напишите @{bot_username} pr КОД для отправки промокода",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"🦔 Промокоды бота Говорящий Еж!\n\n"
                    f"Чтобы поделиться промокодом:\n"
                    f"1. Введите: @{bot_username} pr КОД\n"
                    f"2. Нажмите на результат\n"
                    f"3. Любой пользователь сможет забрать промокод!"
                )
            )
        ))
    
    await query.answer(results, cache_time=5)


@router.callback_query(F.data.startswith("ipromo_"))
async def inline_promo_claim(callback: CallbackQuery):
    """Обработка нажатия на '🔥 Забрать' в inline-сообщении с промокодом."""
    code = callback.data.replace("ipromo_", "")
    user_id = callback.from_user.id
    username = callback.from_user.username or "Unknown"
    
    # Проверка бана
    is_banned, ban_reason = await check_user_banned(user_id)
    if is_banned:
        await callback.answer("🚫 Вы заблокированы!", show_alert=True)
        return
    
    # Авто-регистрация если пользователь новый
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, username)
        user = await get_user(user_id)
    
    if not user:
        await callback.answer("❌ Ошибка регистрации. Нажмите /start в боте и попробуйте снова.", show_alert=True)
        return
    
    # Активация промокода
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # Проверка: уже использовал?
        async with db.execute("SELECT * FROM used_promocodes WHERE user_id = ? AND code = ?", (user_id, code)) as cursor:
            if await cursor.fetchone():
                await callback.answer("❌ Вы уже активировали этот промокод!", show_alert=True)
                return
        
        # Проверка: промокод существует?
        async with db.execute("SELECT * FROM promocodes WHERE code = ? AND uses_left > 0", (code,)) as cursor:
            promo = await cursor.fetchone()
        
        if not promo:
            await callback.answer("❌ Промокод не найден или все активации исчерпаны.", show_alert=True)
            return
        
        # Выдача награды
        reward_type = promo['reward_type']
        reward_value = promo['reward_value']
        
        if reward_type == "balance":
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (int(reward_value), user_id))
            reward_text = f"+{reward_value} Ежидзиков👍"
        elif reward_type == "ants":
            await db.execute("UPDATE users SET ants = ants + ? WHERE user_id = ?", (int(reward_value), user_id))
            reward_text = f"+{reward_value} муравьёв🐜"
        elif reward_type == "color":
            await db.execute("UPDATE users SET hedgehog_color = ? WHERE user_id = ?", (reward_value, user_id))
            reward_text = f"Новый цвет: {reward_value}"
        else:
            reward_text = "Награда получена!"
        
        await db.execute("INSERT INTO used_promocodes (user_id, code, used_at) VALUES (?, ?, ?)", (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.execute("UPDATE promocodes SET uses_left = uses_left - 1, total_uses = total_uses + 1 WHERE code = ?", (code,))
        await db.commit()
    
    # Обновляем inline-кнопку: убираем «Забрать» и показываем «Забрано»
    try:
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Забрано!", callback_data="ipromo_done")]
            ])
        )
    except Exception:
        pass  # сообщение уже изменено или слишком старое
    
    # Пробуем отправить личное сообщение с деталями
    try:
        bot_username = await _get_bot_username()
        await bot.send_message(
            user_id,
            f"🎉 Промокод активирован!\n\n{reward_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🦔 Открыть бота", url=f"https://t.me/{bot_username}")]
            ])
        )
    except Exception:
        pass  # пользователь не начал бота — нельзя написать в ЛС
    
    await callback.answer(f"🎉 Промокод активирован! {reward_text}", show_alert=True)

# =====================================
# 🎰 ДОМАШНЕЕ КАЗИНО
# =====================================

async def get_hc_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT home_casino_balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0

async def update_hc_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET home_casino_balance = home_casino_balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def set_hc_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET home_casino_balance = ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

# --- ГЛАВНОЕ МЕНЮ ---
@router.callback_query(F.data == "hc_casino")
async def hc_casino_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    if not user['home_casino']:
        await safe_edit_text(
            callback.message,
            "🎰 **Домашнее казино**\n\n"
            "Тут можно играть на фейковые Ежедзуки — без риска, чисто по фану!\n\n"
            "• Начисляй себе сколько хочешь\n"
            "• Играй в те же игры что в обычном казино\n"
            "• Ежедзуки ни на что не влияют — это фантики\n\n"
            "💰 Цена: 300 Ежидзиков",
            reply_markup=hc_casino_buy_keyboard(),
            parse_mode="Markdown"
        )
        return
    
    hc_bal = await get_hc_balance(callback.from_user.id)
    await safe_edit_text(
        callback.message,
        f"🎰 **Домашнее казино**\n\n"
        f"💰 Ежедзуков: {hc_bal}\n\n"
        f"Игры те же, что в обычном — но на фанки!",
        reply_markup=hc_casino_keyboard(),
        parse_mode="Markdown"
    )

# --- ПОКУПКА / ПРОДАЖА ---
@router.callback_query(F.data == "hc_buy")
async def hc_buy(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start!", show_alert=True)
        return
    if user['home_casino']:
        await callback.answer("✅ У тебя уже есть казино!", show_alert=True)
        return
    if user['balance'] < 300:
        await callback.answer("❌ Нужно 300 Ежидзиков!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - 300, home_casino = 1, home_casino_balance = 1000 WHERE user_id = ?", (callback.from_user.id,))
        await db.commit()
    
    await safe_edit_text(
        callback.message,
        "🎰 **Домашнее казино**\n\n"
        "✅ Куплено! Начислено 1000 Ежедзуков на баланс\n\n"
        "💰 Ежедзуков: 1000",
        reply_markup=hc_casino_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "hc_sell")
async def hc_sell(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user['home_casino']:
        await callback.answer("❌ У тебя нет казино!", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + 150, home_casino = 0, home_casino_balance = 0 WHERE user_id = ?", (callback.from_user.id,))
        await db.commit()
    
    await safe_edit_text(
        callback.message,
        "🎰 Домашнее казино продано за 150 Ежидзиков 👋",
        reply_markup=back_button("puzzle")
    )

# --- НАЧИСЛЕНИЕ / СНЯТИЕ ФАНТИКОВ ---
@router.callback_query(F.data == "hc_add")
async def hc_add_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HomeCasinoStates.add_balance)
    await state.update_data(hc_action="add")
    await safe_edit_text(
        callback.message,
        "➕ Введи количество Ежедзуков для начисления:",
        reply_markup=back_button("hc_casino")
    )

# hc_add_process вынесен ДО catch-all (см. ниже перед F.text)

@router.callback_query(F.data == "hc_remove")
async def hc_remove_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HomeCasinoStates.add_balance)
    await state.update_data(hc_action="remove")
    await safe_edit_text(
        callback.message,
        "➖ Введи количество Ежедзуков для списания:",
        reply_markup=back_button("hc_casino")
    )

@router.callback_query(F.data == "hc_reset")
async def hc_reset(callback: CallbackQuery):
    await set_hc_balance(callback.from_user.id, 0)
    await safe_edit_text(callback.message, "🔄 Ежедзуки обнулены!", reply_markup=back_button("hc_casino"))

# --- 🎲 КУБИК ---
@router.callback_query(F.data == "hc_dice")
async def hc_dice_menu(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    hc_bal = await get_hc_balance(callback.from_user.id)
    await safe_edit_text(
        callback.message,
        f"🎲 Бросить кубик\n\nВыбери 3 числа от 1 до 6.\nУгадал — ×2, нет — теряешь ставку.\n\n💰 Ежедзуков: {hc_bal}\n\nВыбери ставку:",
        reply_markup=hc_bet_keyboard("dice")
    )

@router.callback_query(F.data.startswith("hc_bet_dice_"), F.data != "hc_bet_dice_custom")
async def hc_bet_dice(callback: CallbackQuery, state: FSMContext):
    bet = int(callback.data.replace("hc_bet_dice_", ""))
    hc_bal = await get_hc_balance(callback.from_user.id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    await state.update_data(bet=bet, selected_numbers=[])
    await state.set_state(HomeCasinoStates.dice_numbers)
    await safe_edit_text(callback.message, f"🎲 Ставка: {bet} Ежедзуков\n\nВыбери 3 числа (1-6):", reply_markup=hc_dice_numbers_keyboard([]))

@router.callback_query(F.data.startswith("hc_dice_num_"), HomeCasinoStates.dice_numbers)
async def hc_dice_select(callback: CallbackQuery, state: FSMContext):
    num = int(callback.data.replace("hc_dice_num_", ""))
    data = await state.get_data()
    selected = data.get('selected_numbers', [])
    if num in selected:
        selected.remove(num)
    elif len(selected) < 3:
        selected.append(num)
    else:
        await callback.answer("Уже выбрано 3 числа!", show_alert=True)
        return
    await state.update_data(selected_numbers=selected)
    await safe_edit_text(callback.message, f"🎲 Ставка: {data['bet']} Ежедзуков\n\nВыбери 3 числа (1-6):\nВыбрано: {selected if selected else 'ничего'}", reply_markup=hc_dice_numbers_keyboard(selected))

@router.callback_query(F.data == "hc_dice_roll", HomeCasinoStates.dice_numbers)
async def hc_dice_roll(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data['bet']
    selected = data['selected_numbers']
    await state.clear()
    
    hc_bal = await get_hc_balance(callback.from_user.id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    
    await update_hc_balance(callback.from_user.id, -bet)
    result = random.randint(1, 6)
    
    if result in selected:
        win = bet * 2
        await update_hc_balance(callback.from_user.id, win)
        await safe_edit_text(callback.message, f"🎲 Кубик показал: {result}\n\n🎉 ПОБЕДА! Твои числа: {selected}\n💰 +{win} Ежедзуков!", reply_markup=back_button("hc_casino"))
    else:
        await safe_edit_text(callback.message, f"🎲 Кубик показал: {result}\n\n😔 Мимо... Числа: {selected}\n💸 -{bet} Ежедзуков", reply_markup=back_button("hc_casino"))

# --- 🦔 ЕЖИНО ---
@router.callback_query(F.data == "hc_ejino")
async def hc_ejino_menu(callback: CallbackQuery):
    hc_bal = await get_hc_balance(callback.from_user.id)
    await safe_edit_text(callback.message, f"🦔 ЕЖИНО — рулетка удачи!\n\nМножители: ×0, ×0.5, ×1, ×1.5, ×2, ×5🔥\n\n💰 Ежедзуков: {hc_bal}\n\nВыбери ставку:", reply_markup=hc_bet_keyboard("ejino"))

@router.callback_query(F.data.startswith("hc_bet_ejino_"), F.data != "hc_bet_ejino_custom")
async def hc_bet_ejino(callback: CallbackQuery, state: FSMContext):
    bet = int(callback.data.replace("hc_bet_ejino_", ""))
    hc_bal = await get_hc_balance(callback.from_user.id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    await state.update_data(bet=bet)
    await safe_edit_text(callback.message, f"🦔 ЕЖИНО\n\nСтавка: {bet} Ежедзуков\n\nКрути!", reply_markup=hc_ejino_keyboard())

@router.callback_query(F.data == "hc_ejino_spin")
async def hc_ejino_spin(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('bet', 0)
    if not bet:
        await callback.answer("❌ Сначала выбери ставку!", show_alert=True)
        return
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    await state.clear()
    
    hc_bal = await get_hc_balance(user_id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    
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
    await update_hc_balance(user_id, profit)
    
    if multiplier == 5: emoji = "🔥🎉🔥"
    elif multiplier >= 2: emoji = "🎉"
    elif multiplier >= 1: emoji = "😐"
    else: emoji = "😔"
    
    spin_text = "🦔 ЕЖИНО крутится... 🎰\n\n"
    await stream_text(chat_id, spin_text, chunk_size=15, delay=0.04)
    await asyncio.sleep(0.5)
    
    result_text = f"🦔 ЕЖИНО — результат!\n\nРезультат: ×{multiplier} {emoji}\n\nСтавка: {bet} → Выигрыш: {win} Ежедзуков"
    try:
        await callback.message.answer(result_text, reply_markup=back_button("hc_casino"))
    except:
        await safe_edit_text(callback.message, result_text, reply_markup=back_button("hc_casino"))

# --- 🎰 СЛОТЫ ---
@router.callback_query(F.data == "hc_slots")
async def hc_slots_menu(callback: CallbackQuery):
    hc_bal = await get_hc_balance(callback.from_user.id)
    await safe_edit_text(callback.message, f"🎰 Слоты\n\n3 разных = ×0\n2 одинаковых = ×1.3\n3 одинаковых = ×2.5\n\n💰 Ежедзуков: {hc_bal}\n\nВыбери ставку:", reply_markup=hc_bet_keyboard("slots"))

@router.callback_query(F.data.startswith("hc_bet_slots_"), F.data != "hc_bet_slots_custom")
async def hc_bet_slots(callback: CallbackQuery, state: FSMContext):
    bet = int(callback.data.replace("hc_bet_slots_", ""))
    hc_bal = await get_hc_balance(callback.from_user.id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    await state.update_data(bet=bet)
    await safe_edit_text(callback.message, f"🎰 Слоты\n\nСтавка: {bet} Ежедзуков", reply_markup=hc_slots_keyboard())

@router.callback_query(F.data == "hc_slots_spin")
async def hc_slots_spin(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('bet', 0)
    if not bet:
        await callback.answer("❌ Сначала выбери ставку!", show_alert=True)
        return
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    await state.clear()
    
    hc_bal = await get_hc_balance(user_id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    
    result = [random.choice(CASINO_EMOJI) for _ in range(3)]
    unique = len(set(result))
    if unique == 1: multiplier = 2.5
    elif unique == 2: multiplier = 1.3
    else: multiplier = 0
    
    win = int(bet * multiplier)
    profit = win - bet
    await update_hc_balance(user_id, profit)
    
    if multiplier == 2.5: emoji = "🎉🎉🎉"
    elif multiplier == 1.3: emoji = "🎉"
    else: emoji = "😔"
    
    slots_text = "🎰 Крутим...\n\n"
    await stream_text(chat_id, slots_text, chunk_size=20, delay=0.04)
    for i in range(3):
        partial = " | ".join(result[:i+1])
        remaining = " ❓ " * (2 - i)
        line = f"[ {partial} {remaining}]"
        draft_id = random.randint(1, 2**31 - 1)
        try:
            await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text=f"🎰 Крутим...\n\n{line}")
            await asyncio.sleep(0.6)
        except: break
    await asyncio.sleep(0.3)
    
    final_text = f"🎰 Результат!\n\n[ {result[0]} | {result[1]} | {result[2]} ]\n\nМножитель: ×{multiplier} {emoji}\n💰 Результат: {win} Ежедзуков"
    try:
        await callback.message.answer(final_text, reply_markup=back_button("hc_casino"))
    except:
        await safe_edit_text(callback.message, final_text, reply_markup=back_button("hc_casino"))

# --- 🌟 ЗВЁЗДЫ ---
@router.callback_query(F.data == "hc_star")
async def hc_star_menu(callback: CallbackQuery):
    hc_bal = await get_hc_balance(callback.from_user.id)
    await safe_edit_text(callback.message, f"🌟 Найди звезду!\n\nПоле 5×5, 5 звёзд ⭐\nЗвезда = ×2.5 от ставки\nПусто = ×0\nКаждое нажатие = ставка\n\n💰 Ежедзуков: {hc_bal}\n\nВыбери ставку за нажатие:", reply_markup=hc_bet_keyboard("star"))

@router.callback_query(F.data.startswith("hc_bet_star_"), F.data != "hc_bet_star_custom")
async def hc_bet_star(callback: CallbackQuery, state: FSMContext):
    bet = int(callback.data.replace("hc_bet_star_", ""))
    hc_bal = await get_hc_balance(callback.from_user.id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    field = ["❌"] * 25
    star_positions = random.sample(range(25), 5)
    for pos in star_positions:
        field[pos] = "⭐"
    await state.update_data(bet=bet, field=field, revealed=[], total_win=0)
    await state.set_state(HomeCasinoStates.star_game)
    await safe_edit_text(callback.message, f"🌟 Найди звезду!\n\nСтавка за нажатие: {bet} Ежедзуков\nВыигрыш: 0\n\nНажимай на ❓!", reply_markup=hc_star_field_keyboard(field, []))

@router.callback_query(F.data.startswith("hc_star_"), HomeCasinoStates.star_game)
async def hc_star_reveal(callback: CallbackQuery, state: FSMContext):
    if callback.data == "hc_star_end":
        data = await state.get_data()
        total_win = data.get('total_win', 0)
        await state.clear()
        await safe_edit_text(callback.message, f"🌟 Игра окончена!\n\n💰 Всего выиграно: {total_win} Ежедзуков", reply_markup=back_button("hc_casino"))
        return
    
    idx = int(callback.data.replace("hc_star_", ""))
    data = await state.get_data()
    bet = data['bet']
    field = data['field']
    revealed = data['revealed']
    total_win = data['total_win']
    user_id = callback.from_user.id
    
    if idx in revealed:
        await callback.answer("Уже открыто!")
        return
    
    hc_bal = await get_hc_balance(user_id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    
    revealed.append(idx)
    await update_hc_balance(user_id, -bet)
    
    if field[idx] == "⭐":
        win = int(bet * 2.5)
        total_win += win
        await update_hc_balance(user_id, win)
        await callback.answer(f"🌟 ЗВЕЗДА! +{win} Ежедзуков!", show_alert=True)
    else:
        await callback.answer(f"❌ Пусто! -{bet} Ежедзуков", show_alert=True)
    
    await state.update_data(revealed=revealed, total_win=total_win)
    new_bal = await get_hc_balance(user_id)
    await safe_edit_text(callback.message, f"🌟 Найди звезду!\n\nСтавка за нажатие: {bet} Ежедзуков\nВыигрыш: {total_win}\n💰 Ежедзуков: {new_bal}\n\nНажимай на ❓!", reply_markup=hc_star_field_keyboard(field, revealed))

# --- ☠️ ×10 ---
@router.callback_query(F.data == "hc_x10")
async def hc_x10_menu(callback: CallbackQuery):
    hc_bal = await get_hc_balance(callback.from_user.id)
    await safe_edit_text(callback.message, f"☠️ ×10 от ставки!\n\nШанс: 5%!\nПобеда = ×10 🔥\nПроигрыш = теряешь ставку 💀\n\n💰 Ежедзуков: {hc_bal}\n\nВыбери ставку:", reply_markup=hc_bet_keyboard("x10"))

@router.callback_query(F.data.startswith("hc_bet_x10_"), F.data != "hc_bet_x10_custom")
async def hc_bet_x10(callback: CallbackQuery, state: FSMContext):
    bet = int(callback.data.replace("hc_bet_x10_", ""))
    hc_bal = await get_hc_balance(callback.from_user.id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    await state.update_data(bet=bet)
    await safe_edit_text(callback.message, f"☠️ ×10 от ставки!\n\nСтавка: {bet} Ежедзуков\n\nТы уверен? Шанс 5%! 💀", reply_markup=hc_x10_keyboard())

@router.callback_query(F.data == "hc_x10_try")
async def hc_x10_try(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('bet', 0)
    if not bet:
        await callback.answer("❌ Сначала выбери ставку!", show_alert=True)
        return
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    await state.clear()
    
    hc_bal = await get_hc_balance(user_id)
    if hc_bal < bet:
        await callback.answer("❌ Недостаточно Ежедзуков!", show_alert=True)
        return
    
    await update_hc_balance(user_id, -bet)
    
    if random.random() < 0.05:
        win = bet * 10
        await update_hc_balance(user_id, win)
        await stream_text(chat_id, "☠️ ×10 ... ", chunk_size=4, delay=0.1)
        await asyncio.sleep(0.8)
        result_text = f"☠️ НЕВЕРОЯТНО! 🔥🎉🔥\n\nТЫ ВЫИГРАЛ ×10!!!\n💰 +{win} Ежедзуков!"
        try:
            await callback.message.answer(result_text, reply_markup=back_button("hc_casino"))
        except:
            await safe_edit_text(callback.message, result_text, reply_markup=back_button("hc_casino"))
    else:
        await stream_text(chat_id, "☠️ ×10 ... ", chunk_size=4, delay=0.1)
        await asyncio.sleep(0.5)
        result_text = f"☠️ Не повезло... 💀\n\n💸 -{bet} Ежедзуков"
        try:
            await callback.message.answer(result_text, reply_markup=back_button("hc_casino"))
        except:
            await safe_edit_text(callback.message, result_text, reply_markup=back_button("hc_casino"))

# --- СВОЯ СТАВКА (общая) ---
@router.callback_query(F.data.startswith("hc_bet_"), F.data.endswith("_custom"))
async def hc_custom_bet_input(callback: CallbackQuery, state: FSMContext):
    game_type = callback.data.split("_")[2]  # hc_bet_dice_custom -> dice
    await state.set_state(HomeCasinoStates.custom_bet_amount)
    await state.update_data(game_type=game_type)
    await safe_edit_text(callback.message, "🖊 Введи сумму ставки (числом):", reply_markup=back_button("hc_casino"))

# ⚠️ FSM-хэндлер ДОЛЖЕН быть до catch-all
# (уже размещён BankStates перед F.text, добавим и HomeCasinoStates туда же)

# =====================================
# 🏦 БАНК «ЁЖ-ФИНАНС»
# =====================================

@router.callback_query(F.data == "bank")
async def bank_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    # Считаем сколько на вкладах
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT SUM(amount) as total, SUM(accrued) as total_accrued FROM bank_deposits WHERE user_id = ? AND status = 'active'", (callback.from_user.id,)) as cursor:
            row = await cursor.fetchone()
    
    total_deposited = row['total'] if row and row['total'] else 0
    total_accrued = row['total_accrued'] if row and row['total_accrued'] else 0
    
    text = (
        f"🏦 **Банк «Ёж-Финанс»**\n\n"
        f"💰 Ваш баланс: {user['balance']} Ежидзиков\n"
        f"📦 На вкладах: {total_deposited} Ежидзиков\n"
        f"📈 Начислено: +{total_accrued} Ежидзиков\n\n"
        f"Кладите Ежидзики под процент и получайте доход!"
    )
    
    await safe_edit_text(callback.message, text, reply_markup=bank_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "bank_info")
async def bank_info(callback: CallbackQuery):
    text = (
        "🏦 **Информация о банке**\n\n"
        "**Виды вкладов:**\n\n"
        "🐾 **До востребования**\n"
        "• Ставка: 0.5%/сут\n"
        "• Мин. сумма: 10 ЕЖ\n"
        "• Снятие в любой момент\n"
        "• Штрафа нет\n\n"
        "🦔 **Стабильный**\n"
        "• Ставка: 1.2%/сут\n"
        "• Мин. сумма: 50 ЕЖ\n"
        "• Заморозка: 24 часа\n"
        "• Досрочное снятие: штраф 10%\n\n"
        "🏆 **Премиум**\n"
        "• Ставка: 2%/сут\n"
        "• Мин. сумма: 500 ЕЖ\n"
        "• Заморозка: 72 часа\n"
        "• Досрочное снятие: штраф 10%\n\n"
        "**Общие правила:**\n"
        f"• Макс. сумма вклада: {BANK_MAX_DEPOSIT:,} ЕЖ\n"
        "• 1 активный вклад каждого типа на человека\n"
        "• Процент начисляется на базовую сумму\n"
        "• Начисление каждый час (пропорционально)\n"
        f"• Налог на процент: {int(BANK_INTEREST_TAX*100)}%\n"
        f"• Штраф за досрочное снятие: {int(BANK_EARLY_PENALTY*100)}%\n"
    )
    await safe_edit_text(callback.message, text, reply_markup=back_button("bank"), parse_mode="Markdown")


@router.callback_query(F.data == "bank_open")
async def bank_open_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    # Проверяем какие типы уже открыты
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT deposit_type FROM bank_deposits WHERE user_id = ? AND status = 'active'", (callback.from_user.id,)) as cursor:
            active = [r['deposit_type'] for r in await cursor.fetchall()]
    
    available = {k: v for k, v in BANK_DEPOSIT_TYPES.items() if k not in active}
    
    if not available:
        await callback.answer("❌ У вас уже есть все виды вкладов!", show_alert=True)
        return
    
    text = (
        f"💰 Открыть вклад\n\n"
        f"Ваш баланс: {user['balance']} Ежидзиков\n\n"
        "Выберите тип вклада:"
    )
    
    buttons = []
    for dtype, info in available.items():
        lock_txt = f" (заморозка {info['lock_hours']}ч)" if info['lock_hours'] > 0 else " (бессрочно)"
        buttons.append([InlineKeyboardButton(
            text=f"{info['name']} — {info['rate']}%/сут{lock_txt}",
            callback_data=f"bank_select_{dtype}"
        )])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="bank")])
    
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("bank_select_"))
async def bank_select_deposit_type(callback: CallbackQuery, state: FSMContext):
    dtype = callback.data.replace("bank_select_", "")
    if dtype not in BANK_DEPOSIT_TYPES:
        await callback.answer("❌ Неизвестный тип вклада!", show_alert=True)
        return
    
    info = BANK_DEPOSIT_TYPES[dtype]
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Нажмите /start сначала!", show_alert=True)
        return
    
    lock_txt = f"Заморозка: {info['lock_hours']}ч" if info['lock_hours'] > 0 else "Снятие в любой момент"
    
    text = (
        f"{info['name']}\n\n"
        f"📊 Ставка: {info['rate']}%/сут\n"
        f"🔒 {lock_txt}\n"
        f"💵 Мин. сумма: {info['min_amount']} ЕЖ\n"
        f"📦 Макс. сумма: {BANK_MAX_DEPOSIT:,} ЕЖ\n\n"
        f"💰 Ваш баланс: {user['balance']} ЕЖ\n\n"
        f"Введите сумму вклада:"
    )
    
    await state.update_data(deposit_type=dtype)
    await state.set_state(BankStates.waiting_deposit_amount)
    
    buttons = [[InlineKeyboardButton(text="❌ Отмена", callback_data="bank_open")]]
    await safe_edit_text(callback.message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "bank_my_deposits")
async def bank_my_deposits(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bank_deposits WHERE user_id = ? AND status = 'active' ORDER BY opened_at", (callback.from_user.id,)) as cursor:
            deposits = await cursor.fetchall()
    
    if not deposits:
        await safe_edit_text(callback.message, "📋 У вас нет активных вкладов.", reply_markup=back_button("bank"))
        return
    
    buttons = []
    for dep in deposits:
        info = BANK_DEPOSIT_TYPES.get(dep['deposit_type'], {})
        name = info.get('name', dep['deposit_type'])
        lock_icon = "🔒" if dep['is_locked'] else "🔓"
        buttons.append([InlineKeyboardButton(
            text=f"{lock_icon} {name} — {dep['amount']} ЕЖ (+{dep['accrued']})",
            callback_data=f"bank_view_{dep['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="Назад ◀️◀️◀️", callback_data="bank")])
    
    await safe_edit_text(callback.message, "📋 **Ваши вклады:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("bank_view_"))
async def bank_view_deposit(callback: CallbackQuery):
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    dep_id = int(callback.data.replace("bank_view_", ""))
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bank_deposits WHERE id = ? AND user_id = ?", (dep_id, callback.from_user.id)) as cursor:
            dep = await cursor.fetchone()
    
    if not dep or dep['status'] != 'active':
        await callback.answer("❌ Вклад не найден!", show_alert=True)
        return
    
    info = BANK_DEPOSIT_TYPES.get(dep['deposit_type'], {})
    name = info.get('name', dep['deposit_type'])
    rate = info.get('rate', 0)
    
    # Проверяем разблокирован ли
    now = datetime.now()
    is_locked = dep['is_locked']
    can_withdraw = not is_locked
    
    if is_locked and dep['unlock_at']:
        unlock_dt = datetime.strptime(dep['unlock_at'], "%Y-%m-%d %H:%M:%S")
        if now >= unlock_dt:
            can_withdraw = True
            is_locked = False
    
    # Считаем примерный доход за сутки
    daily_income = int(dep['amount'] * rate / 100 * (1 - BANK_INTEREST_TAX))
    
    lock_txt = ""
    if dep['is_locked'] and dep['unlock_at']:
        unlock_dt = datetime.strptime(dep['unlock_at'], "%Y-%m-%d %H:%M:%S")
        remaining = unlock_dt - now
        if remaining.total_seconds() > 0:
            hours_left = int(remaining.total_seconds() / 3600)
            mins_left = int((remaining.total_seconds() % 3600) / 60)
            lock_txt = f"\n🔒 Заморожен ещё: {hours_left}ч {mins_left}м"
        else:
            lock_txt = "\n🔓 Разблокирован! Можно снять"
    else:
        lock_txt = "\n🔓 Можно снять в любой момент"
    
    penalty_txt = ""
    if is_locked and not can_withdraw:
        penalty = int(dep['amount'] * BANK_EARLY_PENALTY)
        penalty_txt = f"\n⚠️ Штраф за досрочное снятие: {penalty} ЕЖ"
    
    text = (
        f"🏦 **{name}**\n\n"
        f"💵 Сумма вклада: {dep['amount']} ЕЖ\n"
        f"📈 Начислено: +{dep['accrued']} ЕЖ\n"
        f"📊 Ставка: {rate}%/сут\n"
        f"💰 Доход в сутки: ~{daily_income} ЕЖ\n"
        f"📅 Открыт: {dep['opened_at']}"
        f"{lock_txt}"
        f"{penalty_txt}"
    )
    
    await safe_edit_text(callback.message, text, reply_markup=bank_deposit_actions_keyboard(dep_id, can_withdraw, is_locked and not can_withdraw), parse_mode="Markdown")


@router.callback_query(F.data.startswith("bank_withdraw_"))
async def bank_withdraw_deposit(callback: CallbackQuery):
    """Снять вклад (без штрафа — срок прошёл или до востребования)"""
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    dep_id = int(callback.data.replace("bank_withdraw_", ""))
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bank_deposits WHERE id = ? AND user_id = ? AND status = 'active'", (dep_id, callback.from_user.id)) as cursor:
            dep = await cursor.fetchone()
        
        if not dep:
            await callback.answer("❌ Вклад не найден!", show_alert=True)
            return
        
        # Проверяем что можно снять
        if dep['is_locked'] and dep['unlock_at']:
            unlock_dt = datetime.strptime(dep['unlock_at'], "%Y-%m-%d %H:%M:%S")
            if datetime.now() < unlock_dt:
                await callback.answer("❌ Вклад ещё заморожен! Используйте досрочное снятие.", show_alert=True)
                return
        
        total = dep['amount'] + dep['accrued']
        
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (total, callback.from_user.id))
        await db.execute("UPDATE bank_deposits SET status = 'withdrawn' WHERE id = ?", (dep_id,))
        await db.commit()
    
    info = BANK_DEPOSIT_TYPES.get(dep['deposit_type'], {})
    name = info.get('name', dep['deposit_type'])
    
    await safe_edit_text(
        callback.message,
        f"✅ Вклад снят!\n\n"
        f"🏦 {name}\n"
        f"💵 Вклад: {dep['amount']} ЕЖ\n"
        f"📈 Начислено: +{dep['accrued']} ЕЖ\n"
        f"💰 Итого получено: {total} ЕЖ",
        reply_markup=back_button("bank")
    )


@router.callback_query(F.data.startswith("bank_early_"))
async def bank_early_withdraw(callback: CallbackQuery):
    """Досрочное снятие со штрафом"""
    if not await check_access(bot, callback.from_user.id, callback):
        return
    
    dep_id = int(callback.data.replace("bank_early_", ""))
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bank_deposits WHERE id = ? AND user_id = ? AND status = 'active'", (dep_id, callback.from_user.id)) as cursor:
            dep = await cursor.fetchone()
        
        if not dep:
            await callback.answer("❌ Вклад не найден!", show_alert=True)
            return
        
        if not dep['is_locked']:
            await callback.answer("❌ Этот вклад не заморожен, снимайте обычным способом!", show_alert=True)
            return
        
        # Штраф: 10% от базовой суммы
        penalty = int(dep['amount'] * BANK_EARLY_PENALTY)
        total_back = dep['amount'] - penalty + dep['accrued']
        if total_back < 0:
            total_back = 0
        
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (total_back, callback.from_user.id))
        await db.execute("UPDATE bank_deposits SET status = 'early_withdrawn' WHERE id = ?", (dep_id,))
        await db.commit()
    
    info = BANK_DEPOSIT_TYPES.get(dep['deposit_type'], {})
    name = info.get('name', dep['deposit_type'])
    
    await safe_edit_text(
        callback.message,
        f"⚠️ Досрочное снятие вклада\n\n"
        f"🏦 {name}\n"
        f"💵 Вклад: {dep['amount']} ЕЖ\n"
        f"📈 Начислено: +{dep['accrued']} ЕЖ\n"
        f"❌ Штраф ({int(BANK_EARLY_PENALTY*100)}%): -{penalty} ЕЖ\n"
        f"💰 Итого получено: {total_back} ЕЖ",
        reply_markup=back_button("bank")
    )


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


async def mining_loop():
    """Фоновая задача майнинга — раз в час."""
    while True:
        try:
            elec_rate = float(await get_setting("mining_electricity_rate", "1"))
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                # Получаем всех майнеров
                async with db.execute("SELECT * FROM mining_state WHERE is_mining = 1") as cursor:
                    miners = await cursor.fetchall()

                for miner in miners:
                    user_id = miner['user_id']
                    # Получаем активные риги
                    async with db.execute("SELECT * FROM mining_rigs WHERE user_id = ? AND is_active = 1", (user_id,)) as cursor:
                        rigs = await cursor.fetchall()

                    if not rigs:
                        continue

                    total_mh = 0
                    total_power = 0
                    max_break_reduction = 0

                    for rig in rigs:
                        # GPU хешрейт и потребление
                        async with db.execute("SELECT mh_rate, power_w FROM mining_components WHERE id = ?", (rig['gpu_id'],)) as cursor:
                            gpu = await cursor.fetchone()
                        if gpu:
                            total_mh += gpu['mh_rate']
                            total_power += gpu['power_w']

                        # Охлаждение
                        if rig['cooling_id']:
                            async with db.execute("SELECT break_reduction FROM mining_components WHERE id = ?", (rig['cooling_id'],)) as cursor:
                                cool = await cursor.fetchone()
                            if cool:
                                max_break_reduction = max(max_break_reduction, cool['break_reduction'])

                    # Электричество
                    elec_cost = int((total_power / 10) * elec_rate)
                    if elec_cost <= 0:
                        elec_cost = 1

                    # Проверяем баланс на электричество
                    async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        user = await cursor.fetchone()
                    if not user or user['balance'] < elec_cost:
                        # Не хватает на электричество — останавливаем майнинг
                        await db.execute("UPDATE mining_state SET is_mining = 0 WHERE user_id = ?", (user_id,))
                        await db.execute("UPDATE mining_rigs SET is_active = 0 WHERE user_id = ?", (user_id,))
                        continue

                    # Списываем электричество
                    await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (elec_cost, user_id))

                    # Рассчитываем добычу
                    coins_mined = total_mh * 0.05 * random.uniform(0.8, 1.2)

                    # Поломки (5% базовый шанс за цикл, снижается охлаждением)
                    break_chance = 0.05 * (1 - max_break_reduction)
                    broken_msg = ""
                    if random.random() < break_chance:
                        # Случайный активный риг ломается
                        broken_rig = random.choice(rigs)
                        # Отмечаем видеокарту как сломанную в риге
                        await db.execute("UPDATE mining_rigs SET is_active = 0 WHERE id = ?", (broken_rig['id'],))
                        # Добавляем сломанную единицу в инвентарь
                        await db.execute('''
                            INSERT INTO mining_inventory (user_id, component_id, quantity, is_broken)
                            VALUES (?, ?, 1, 1)
                            ON CONFLICT(user_id, component_id) DO UPDATE SET is_broken = is_broken + 1
                        ''', (user_id, broken_rig['gpu_id']))
                        broken_msg = " 💥 Поломка!"

                    # Начисляем Ежкоины
                    await db.execute(
                        "UPDATE mining_state SET ezhcoins = ezhcoins + ?, total_mined = total_mined + ?, last_mine = ? WHERE user_id = ?",
                        (coins_mined, coins_mined, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
                    )

                await db.commit()

        except Exception as e:
            print(f"Ошибка майнинг-цикла: {e}")
        await asyncio.sleep(3600)


async def bank_interest_loop():
    """Начисление процентов по вкладам — раз в час."""
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM bank_deposits WHERE status = 'active'") as cursor:
                    deposits = await cursor.fetchall()
                
                for dep in deposits:
                    info = BANK_DEPOSIT_TYPES.get(dep['deposit_type'])
                    if not info:
                        continue
                    
                    # Процент за час = (суточная_ставка / 24)
                    hourly_rate = info['rate'] / 24 / 100  # доля от суммы за 1 час
                    interest = dep['amount'] * hourly_rate
                    
                    # Налог 5%
                    tax = interest * BANK_INTEREST_TAX
                    net_interest = interest - tax
                    
                    # Округляем до целых (минимум 0)
                    net_int = max(0, int(net_interest))
                    
                    if net_int > 0:
                        await db.execute("UPDATE bank_deposits SET accrued = accrued + ? WHERE id = ?", (net_int, dep['id']))
                
                await db.commit()
        except Exception as e:
            print(f"Ошибка начисления процентов банка: {e}")
        await asyncio.sleep(3600)


async def hunger_loop():
    # Реализация механики выживания v5
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
        
        # Удаляем вебхук и сбрасываем ожидающие обновления (на случай конфликта инстансов)
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            print("✅ Вебхук удалён, pending updates сброшены")
        except Exception as e:
            print(f"⚠️ Не удалось удалить вебхук: {e}")
        
        # Проверяем подключение к Telegram
        try:
            me = await bot.get_me()
            print(f"✅ Подключение к Telegram OK: @{me.username} (id: {me.id})")
        except Exception as e:
            print(f"❌ Не удалось подключиться к Telegram API: {e}")
            return
        
        # Start background tasks
        # Инициализируем кеш bot username
        await _get_bot_username()
        asyncio.create_task(ant_income_loop())
        asyncio.create_task(mining_loop())
        asyncio.create_task(bank_interest_loop())
        asyncio.create_task(hunger_loop())
        
        # Start web server (non-blocking!)
        try:
            from web import start_web_server
            asyncio.create_task(start_web_server())
        except Exception as e:
            print(f"⚠️ Web-сервер не запущен: {e}")
        
        print("=" * 50)
        print("🦔 Бот 'Говорящий Еж' v5 (Casino & Banking Update) запущен!")
        print("=" * 50)
        print(f"👑 Главный админ: @{MAIN_ADMIN_USERNAME}")
        print(f"📢 Канал: {CHANNEL_LINK}")
        print("=" * 50)
        
        await dp.start_polling(bot, handle_updates_errors=True)
    except Exception as e:
        print(f"❌ ФАТАЛЬНАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
