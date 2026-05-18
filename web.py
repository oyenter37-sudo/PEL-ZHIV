# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - WEB INTERFACE v5 🦔
# =====================================
# Веб-интерфейс для Telegram-бота
# Запускается параллельно с ботом на порту 8080

import os
import json
import secrets
import asyncio
from datetime import datetime, timedelta

import aiosqlite
from aiohttp import web

DB_NAME = os.environ.get("DB_NAME", "hedgehog_bot.db")

# Публичный URL — хост пробрасывает порт 8080 сюда
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://ezikezik.b.jrnm.app")

# =====================================
# 🎨 КОНСТАНТЫ (как в боте)
# =====================================

COLORS = {
    "black": "⚫ Чёрный", "brown": "🟤 Коричневый", "white": "⚪ Белый",
    "orange": "🟠 Оранжевый", "gold": "🟡 Золотой", "blue": "🔵 Синий",
    "purple": "🟣 Фиолетовый", "red": "🔴 Красный", "green": "🟢 Зелёный",
    "rainbow": "🌈 Радужный",
}

CLASSES = {
    "normal": {"name": "Обычный Еж 🦔", "price": 220, "max_satiety": 100},
    "ejidze": {"name": "Ежидзе 🤠", "price": 350, "max_satiety": 100},
    "fat":    {"name": "Толстый Еж 🦔", "price": 300, "max_satiety": 200},
    "golden": {"name": "Золотой Еж 🟡", "price": 600, "max_satiety": 100},
}

# =====================================
# 🎨 HTML / CSS ШАБЛОНЫ
# =====================================

def get_base_css():
    return """
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        min-height: 100vh;
        color: #e0e0e0;
        overflow-x: hidden;
    }

    body::before {
        content: '';
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background:
            radial-gradient(circle at 20% 80%, rgba(120, 50, 255, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(255, 50, 150, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(50, 150, 255, 0.08) 0%, transparent 60%);
        pointer-events: none;
        z-index: 0;
        animation: bgPulse 8s ease-in-out infinite alternate;
    }

    @keyframes bgPulse {
        0% { opacity: 0.6; }
        100% { opacity: 1; }
    }

    .container {
        position: relative;
        z-index: 1;
        max-width: 480px;
        margin: 0 auto;
        padding: 20px 16px;
    }

    .card {
        background: rgba(255, 255, 255, 0.06);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 16px;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(120, 50, 255, 0.2);
    }

    .header {
        text-align: center;
        padding: 30px 0 20px;
    }
    .header h1 {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa, #f472b6, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 6px;
    }
    .header .subtitle {
        color: rgba(255,255,255,0.5);
        font-size: 13px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .nav {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 16px;
    }
    .nav a {
        flex: 1 1 calc(33% - 6px);
        min-width: 80px;
        text-align: center;
        padding: 10px 6px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: 600;
        font-size: 12px;
        transition: all 0.25s;
        background: rgba(255,255,255,0.05);
        color: rgba(255,255,255,0.6);
        border: 1px solid rgba(255,255,255,0.08);
    }
    .nav a.active {
        background: linear-gradient(135deg, rgba(120,50,255,0.3), rgba(255,50,150,0.2));
        color: #fff;
        border-color: rgba(120,50,255,0.4);
        box-shadow: 0 4px 20px rgba(120,50,255,0.15);
    }
    .nav a:hover:not(.active) {
        background: rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.9);
    }

    .stat-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .stat-row:last-child { border-bottom: none; }
    .stat-label {
        color: rgba(255,255,255,0.55);
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .stat-value {
        font-weight: 700;
        font-size: 16px;
        color: #fff;
    }
    .stat-value.gold { color: #fbbf24; }
    .stat-value.blue { color: #60a5fa; }
    .stat-value.pink { color: #f472b6; }
    .stat-value.green { color: #34d399; }
    .stat-value.purple { color: #a78bfa; }
    .stat-value.red { color: #f87171; }

    .progress-wrap { margin-top: 4px; }
    .progress-bar {
        height: 8px;
        border-radius: 4px;
        background: rgba(255,255,255,0.08);
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.6s ease;
    }
    .progress-fill.green { background: linear-gradient(90deg, #34d399, #10b981); }
    .progress-fill.yellow { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
    .progress-fill.red { background: linear-gradient(90deg, #f87171, #ef4444); }

    .section-title {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: rgba(255,255,255,0.35);
        margin: 20px 0 10px;
        padding-left: 4px;
    }

    .deposit-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .deposit-type { font-weight: 700; font-size: 15px; margin-bottom: 6px; }
    .deposit-info { font-size: 13px; color: rgba(255,255,255,0.5); }

    .login-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }
    .login-card { width: 100%; max-width: 400px; }
    .login-card h2 {
        text-align: center;
        font-size: 22px;
        margin-bottom: 6px;
        background: linear-gradient(135deg, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .login-card .hint {
        text-align: center;
        color: rgba(255,255,255,0.4);
        font-size: 13px;
        margin-bottom: 24px;
    }
    .input-group { margin-bottom: 12px; }
    .input-group input, .input-group select {
        width: 100%;
        padding: 14px 18px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.06);
        color: #fff;
        font-size: 16px;
        outline: none;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .input-group select option { background: #1e1b4b; color: #fff; }
    .input-group input:focus, .input-group select:focus {
        border-color: rgba(120,50,255,0.5);
        box-shadow: 0 0 20px rgba(120,50,255,0.15);
    }
    .input-group input::placeholder { color: rgba(255,255,255,0.3); }
    .input-group label {
        display: block;
        font-size: 13px;
        color: rgba(255,255,255,0.5);
        margin-bottom: 6px;
        font-weight: 600;
    }

    .btn {
        width: 100%;
        padding: 14px;
        border-radius: 14px;
        border: none;
        font-size: 16px;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.25s;
    }
    .btn-primary {
        background: linear-gradient(135deg, #7c3aed, #db2777);
        color: #fff;
    }
    .btn-primary:hover {
        box-shadow: 0 6px 24px rgba(120,50,255,0.3);
        transform: translateY(-1px);
    }
    .btn-sm {
        padding: 10px 16px;
        font-size: 13px;
        border-radius: 12px;
        width: auto;
        display: inline-block;
    }
    .btn-green {
        background: linear-gradient(135deg, #10b981, #059669);
        color: #fff;
    }
    .btn-green:hover { box-shadow: 0 4px 16px rgba(16,185,129,0.3); }
    .btn-blue {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: #fff;
    }
    .btn-blue:hover { box-shadow: 0 4px 16px rgba(59,130,246,0.3); }
    .btn-red {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: #fff;
    }
    .btn-logout {
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.5);
        font-size: 13px;
        padding: 10px;
        margin-top: 10px;
    }
    .btn-logout:hover {
        background: rgba(248,113,113,0.15);
        color: #f87171;
    }

    .error-msg {
        text-align: center;
        color: #f87171;
        font-size: 14px;
        margin-bottom: 12px;
        display: none;
        padding: 10px;
        border-radius: 12px;
        background: rgba(248,113,113,0.1);
    }
    .success-msg {
        text-align: center;
        color: #34d399;
        font-size: 14px;
        margin-bottom: 12px;
        padding: 10px;
        border-radius: 12px;
        background: rgba(52,211,153,0.1);
    }

    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-alive { background: rgba(52,211,153,0.15); color: #34d399; }
    .badge-dead { background: rgba(248,113,113,0.15); color: #f87171; }
    .badge-admin { background: rgba(167,139,250,0.15); color: #a78bfa; }

    .hedgehog-icon {
        font-size: 48px;
        text-align: center;
        animation: bounce 2s ease-in-out infinite;
    }
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
    }

    /* Топ таблица */
    .top-list { list-style: none; }
    .top-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .top-item:last-child { border-bottom: none; }
    .top-medal {
        font-size: 20px;
        width: 30px;
        text-align: center;
        flex-shrink: 0;
    }
    .top-info { flex: 1; }
    .top-name { font-weight: 700; font-size: 14px; }
    .top-cls { font-size: 11px; color: rgba(255,255,255,0.4); }
    .top-val { font-weight: 800; font-size: 16px; color: #fbbf24; }
    .top-period-nav {
        display: flex;
        gap: 6px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }
    .top-period-nav a {
        padding: 6px 12px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
        text-decoration: none;
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.5);
        border: 1px solid rgba(255,255,255,0.08);
        transition: all 0.2s;
    }
    .top-period-nav a.active {
        background: rgba(120,50,255,0.3);
        color: #fff;
        border-color: rgba(120,50,255,0.5);
    }
    .top-period-nav a:hover:not(.active) {
        background: rgba(255,255,255,0.1);
        color: #fff;
    }

    /* Сетка кнопок цветов */
    .color-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
    }
    .color-btn {
        display: block;
        padding: 10px;
        border-radius: 12px;
        text-align: center;
        text-decoration: none;
        font-weight: 600;
        font-size: 13px;
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.7);
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.2s;
    }
    .color-btn:hover {
        background: rgba(120,50,255,0.2);
        color: #fff;
        border-color: rgba(120,50,255,0.4);
    }
    .color-btn.current {
        background: rgba(120,50,255,0.3);
        border-color: rgba(120,50,255,0.5);
        color: #fff;
    }

    /* Обменник */
    .exchange-direction {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
    }
    .exchange-direction a {
        flex: 1;
        text-align: center;
        padding: 10px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: 600;
        font-size: 13px;
        background: rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.5);
        border: 1px solid rgba(255,255,255,0.08);
        transition: all 0.2s;
    }
    .exchange-direction a.active {
        background: rgba(120,50,255,0.3);
        color: #fff;
        border-color: rgba(120,50,255,0.5);
    }
    .exchange-direction a:hover:not(.active) {
        background: rgba(255,255,255,0.1);
        color: #fff;
    }
    .exchange-rate {
        text-align: center;
        color: rgba(255,255,255,0.4);
        font-size: 13px;
        margin-bottom: 12px;
    }

    /* Бонус */
    .bonus-card {
        text-align: center;
    }
    .bonus-amount {
        font-size: 48px;
        font-weight: 800;
        background: linear-gradient(135deg, #fbbf24, #f59e0b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .bonus-timer {
        font-size: 18px;
        color: rgba(255,255,255,0.5);
        margin-top: 8px;
    }

    @media (max-width: 500px) {
        .container { padding: 12px; }
        .card { padding: 18px; border-radius: 16px; }
        .header h1 { font-size: 24px; }
        .nav a { font-size: 11px; padding: 8px 4px; }
    }
    """


def render_page(title: str, nav_section: str, content: str):
    """Общий шаблон страницы с навигацией."""
    nav_items = [
        ("🦔", "/hedgehog", "hedgehog"),
        ("💰", "/finances", "finances"),
        ("🏆", "/tops", "tops"),
        ("🎨", "/customize", "customize"),
        ("🎁", "/bonus", "bonus"),
        ("♻️", "/exchange", "exchange"),
        ("💸", "/transfer", "transfer"),
    ]
    nav_html = ""
    for emoji, href, section in nav_items:
        active = ' class="active"' if section == nav_section else ''
        nav_html += f'<a href="{href}"{active}>{emoji}</a>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{get_base_css()}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🦔 Говорящий Ёж</h1>
        <div class="subtitle">Личный кабинет</div>
    </div>
    <div class="nav">{nav_html}</div>
    {content}
    <form method="POST" action="/logout">
        <button type="submit" class="btn btn-logout">Выйти</button>
    </form>
</div>
</body>
</html>"""


def render_login(error: str = ""):
    err_style = 'style="display:block"' if error else ''
    err_text = "Неверный ключ входа" if error else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🦔 Говорящий Ёж</title>
    <style>{get_base_css()}</style>
</head>
<body>
<div class="container login-wrap">
    <div class="login-card card">
        <div class="hedgehog-icon">🦔</div>
        <h2>Говорящий Ёж</h2>
        <p class="hint">Введите ключ входа, полученный в боте</p>
        <div class="error-msg" {err_style}>{err_text}</div>
        <form method="POST" action="/login">
            <div class="input-group">
                <input type="text" name="key" placeholder="pel_..." autofocus required>
            </div>
            <button type="submit" class="btn btn-primary">Войти</button>
        </form>
    </div>
</div>
</body>
</html>"""


# =====================================
# 🗄️ РАБОТА С БАЗОЙ ДАННЫХ
# =====================================

async def generate_web_key(user_id: int) -> str:
    key = f"pel_{secrets.token_urlsafe(24)}"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM web_keys WHERE user_id = ?", (user_id,))
        await db.execute(
            "INSERT INTO web_keys (key, user_id, created_at) VALUES (?, ?, ?)",
            (key, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        await db.commit()
    return key


async def validate_web_key(key: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM web_keys WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            try:
                created = datetime.strptime(row['created_at'], "%Y-%m-%d %H:%M:%S")
                if datetime.now() - created > timedelta(hours=1):
                    await db.execute("DELETE FROM web_keys WHERE key = ?", (key,))
                    await db.commit()
                    return None
            except:
                return None
            return row['user_id']


async def get_user_data(user_id: int) -> dict:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def get_bank_deposits(user_id: int) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bank_deposits WHERE user_id = ? AND status = 'active'", (user_id,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_m1ning_data(user_id: int) -> dict:
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM m1ning_state WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default


async def get_top_users(order_by: str, limit: int = 10):
    allowed = {"balance", "elephant_skin", "total_feedings", "referrals_count", "diamonds"}
    if order_by not in allowed:
        order_by = "balance"
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT hedgehog_name, hedgehog_color, player_number, hedgehog_class, {order_by} as value FROM users ORDER BY {order_by} DESC LIMIT ?",
            (limit,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_top_by_stats(action_type: str, period: str, limit: int = 10):
    period_map = {
        "hour": timedelta(hours=1),
        "day": timedelta(hours=24),
        "week": timedelta(days=7),
        "month": timedelta(days=30),
    }
    if period in period_map:
        since = (datetime.now() - period_map[period]).strftime("%Y-%m-%d %H:%M:%S")
    else:
        since = "2000-01-01 00:00:00"

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT u.hedgehog_name, u.hedgehog_color, u.player_number, u.hedgehog_class,
                      COALESCE(SUM(s.amount), 0) as value
               FROM users u
               LEFT JOIN stats s ON s.user_id = u.user_id AND s.action_type = ? AND s.timestamp >= ?
               GROUP BY u.user_id
               HAVING value > 0
               ORDER BY value DESC LIMIT ?""",
            (action_type, since, limit)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def find_user_flexible(query: str):
    """Ищет пользователя по номеру, username или ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = query.strip().lstrip('@')

        # По номеру игрока
        if query.startswith('#'):
            try:
                num = int(query[1:])
                async with db.execute("SELECT * FROM users WHERE player_number = ?", (num,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return dict(row)
            except ValueError:
                pass

        # По ID
        try:
            uid = int(query)
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        except ValueError:
            pass

        # По username
        async with db.execute("SELECT * FROM users WHERE username = ?", (query,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)

        return None


async def get_b1tcoin_rate() -> float:
    base_rate = float(await get_setting("m1ning_base_coin_rate", "0.5"))
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COALESCE(SUM(total_mined), 0) as tm FROM m1ning_state") as cursor:
            row = await cursor.fetchone()
            total_mined = row[0] if row else 0
    rate = base_rate * 45 / (1 + total_mined / 10000)
    return max(rate, 0.1)


# =====================================
# 🌐 ОБРАБОТЧИКИ ЗАПРОСОВ
# =====================================

async def _get_auth_user(request):
    """Возвращает (user_id, user_data) или перенаправляет на логин."""
    session_key = request.cookies.get('session_key', '')
    user_id = await validate_web_key(session_key)
    if not user_id:
        return None, None
    user_data = await get_user_data(user_id)
    if not user_data:
        return None, None
    return user_id, user_data


# --- Логин / Выход ---

async def handle_index(request):
    session_key = request.cookies.get('session_key', '')
    user_id = await validate_web_key(session_key)
    if user_id:
        return web.HTTPFound('/hedgehog')
    return web.Response(text=render_login(), content_type='text/html')


async def handle_login(request):
    if request.method == 'GET':
        session_key = request.cookies.get('session_key', '')
        user_id = await validate_web_key(session_key)
        if user_id:
            return web.HTTPFound('/hedgehog')
        return web.Response(text=render_login(), content_type='text/html')

    data = await request.post()
    key = data.get('key', '').strip()
    user_id = await validate_web_key(key)
    if not user_id:
        return web.Response(text=render_login(error="1"), content_type='text/html')

    resp = web.HTTPFound('/hedgehog')
    resp.set_cookie('session_key', key, max_age=3600, httponly=True)
    return resp


async def handle_logout(request):
    session_key = request.cookies.get('session_key', '')
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM web_keys WHERE key = ?", (session_key,))
        await db.commit()
    resp = web.HTTPFound('/')
    resp.del_cookie('session_key')
    return resp


# --- Мой Ёж ---

async def handle_hedgehog(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    join_date = user_data.get('join_date', '')
    days_in_bot = 0
    if join_date:
        try:
            jd = datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
            days_in_bot = (datetime.now() - jd).days
        except:
            pass

    satiety = int(user_data.get('satiety', 100))
    sat_class = "green" if satiety > 60 else "yellow" if satiety > 25 else "red"
    status_badge = '<span class="badge badge-alive">Жив</span>' if user_data.get('status') == 'alive' else '<span class="badge badge-dead">Мёртв</span>'
    cls_name = CLASSES.get(user_data.get('hedgehog_class', 'normal'), {}).get('name', 'Неизвестно')
    color_name = COLORS.get(user_data.get('hedgehog_color'), user_data.get('hedgehog_color', 'Не выбран'))

    content = f"""
    <div class="card">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
            <div style="font-size:40px">🦔</div>
            <div>
                <div style="font-size:20px;font-weight:800">{user_data.get('hedgehog_name', '🦔Ежъ🦔')}</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.5)">{cls_name} &nbsp;{status_badge}</div>
            </div>
        </div>
        <div class="stat-row">
            <span class="stat-label">🎫 Номер игрока</span>
            <span class="stat-value">#{user_data.get('player_number', 0):04d}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">🎨 Цвет иголок</span>
            <span class="stat-value" style="font-size:14px">{color_name}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">🍖 Сытость</span>
            <span class="stat-value {'green' if satiety > 60 else 'red' if satiety < 25 else 'gold'}">{satiety}%</span>
        </div>
        <div class="progress-wrap">
            <div class="progress-bar">
                <div class="progress-fill {sat_class}" style="width:{min(satiety, 100)}%"></div>
            </div>
        </div>
        <div class="stat-row">
            <span class="stat-label">🕘 Дней в боте</span>
            <span class="stat-value purple">{days_in_bot}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">👬 Приглашено друзей</span>
            <span class="stat-value">{user_data.get('referrals_count', 0)}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">🎁 Заработано с друзей</span>
            <span class="stat-value gold">{user_data.get('referrals_earned', 0)} Еж.</span>
        </div>
    </div>"""

    html = render_page("🦔 Говорящий Ёж — Мой Ёж", "hedgehog", content)
    return web.Response(text=html, content_type='text/html')


# --- Финансы ---

async def handle_finances(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    bank_deposits = await get_bank_deposits(user_id)
    m1ning = await get_m1ning_data(user_id)
    b1tcoins = m1ning.get('b1tcoins', 0)

    # Вклады
    deposits_html = ""
    dep_type_names = {"demand": "📦 До востребования", "stable": "🏦 Стабильный", "premium": "👑 Премиум"}
    dep_rates = {"demand": "0.5%", "stable": "1.2%", "premium": "2.0%"}
    for dep in bank_deposits:
        dname = dep_type_names.get(dep['deposit_type'], dep['deposit_type'])
        drate = dep_rates.get(dep['deposit_type'], "?")
        unlock_text = ""
        if dep.get('unlock_at') and dep.get('is_locked'):
            try:
                unlock_dt = datetime.strptime(dep['unlock_at'], "%Y-%m-%d %H:%M:%S")
                remaining = unlock_dt - datetime.now()
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    mins = int((remaining.total_seconds() % 3600) // 60)
                    unlock_text = f" &bull; 🔒 {hours}ч {mins}м"
                else:
                    unlock_text = " &bull; ✅ Разблокирован"
            except:
                pass
        deposits_html += f"""
        <div class="deposit-card">
            <div class="deposit-type">{dname} <span style="font-size:12px;color:rgba(255,255,255,0.4)">{drate}/день</span></div>
            <div class="deposit-info">💰 {dep['amount']} Еж. &bull; 📈 {dep['accrued']} Еж.{unlock_text}</div>
        </div>"""
    if not deposits_html:
        deposits_html = '<div style="text-align:center;color:rgba(255,255,255,0.3);padding:20px">Нет активных вкладов</div>'

    casino_profit = user_data.get('total_casino_profit', 0)
    casino_profit_color = "green" if casino_profit >= 0 else "red"
    casino_profit_sign = "+" if casino_profit >= 0 else ""

    content = f"""
    <div class="card">
        <div class="section-title">Баланс</div>
        <div class="stat-row">
            <span class="stat-label">👍 Ежидзики</span>
            <span class="stat-value gold">{user_data.get('balance', 0):,}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">🐘 Кожа слона</span>
            <span class="stat-value blue">{user_data.get('elephant_skin', 0):,}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">💎 Алмазы</span>
            <span class="stat-value pink">{user_data.get('diamonds', 0):,}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">⛏️ бNтk0ины</span>
            <span class="stat-value purple">{b1tcoins:,.2f}</span>
        </div>
    </div>
    <div class="card">
        <div class="section-title">Казино</div>
        <div class="stat-row">
            <span class="stat-label">🎉 Побед</span>
            <span class="stat-value green">{user_data.get('casino_wins', 0)}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">😔 Поражений</span>
            <span class="stat-value red">{user_data.get('casino_losses', 0)}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">📊 Профит</span>
            <span class="stat-value {casino_profit_color}">{casino_profit_sign}{casino_profit:,} Еж.</span>
        </div>
    </div>
    <div class="card">
        <div class="section-title">🏦 Вклады</div>
        {deposits_html}
    </div>"""

    html = render_page("🦔 Говорящий Ёж — Финансы", "finances", content)
    return web.Response(text=html, content_type='text/html')


# --- Топы ---

async def handle_tops(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    category = request.query.get('cat', 'balance')
    period = request.query.get('period', 'all')

    # Категории топов
    categories = [
        ("balance", "👍 Ежидзики"),
        ("elephant_skin", "🐘 Кожа слона"),
        ("diamonds", "💎 Алмазы"),
        ("total_feedings", "🍖 Кормления"),
        ("referrals_count", "👬 Рефералы"),
    ]
    cat_html = '<div class="top-period-nav">'
    for cat_key, cat_name in categories:
        active = ' class="active"' if cat_key == category else ''
        cat_html += f'<a href="/tops?cat={cat_key}&period={period}"{active}>{cat_name}</a>'
    cat_html += '</div>'

    # Периоды (для balance и feedings)
    periods_html = ""
    if category in ("balance", "total_feedings"):
        period_options = [("all", "За всё"), ("month", "Месяц"), ("week", "Неделя"), ("day", "День"), ("hour", "Час")]
        stat_type = "balance_add" if category == "balance" else "feeding"
        periods_html = '<div class="top-period-nav">'
        for p_key, p_name in period_options:
            active = ' class="active"' if p_key == period else ''
            periods_html += f'<a href="/tops?cat={category}&period={p_key}"{active}>{p_name}</a>'
        periods_html += '</div>'

    # Получаем данные
    if category in ("balance", "total_feedings") and period != "all":
        stat_type = "balance_add" if category == "balance" else "feeding"
        top_users = await get_top_by_stats(stat_type, period, 10)
    else:
        top_users = await get_top_users(category, 10)

    # Формируем список
    list_html = '<ul class="top-list">'
    for i, u in enumerate(top_users):
        medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, f"{i+1}.")
        cls_icon = "🤠" if u.get('hedgehog_class') == 'ejidze' else "🦔"
        val = u.get('value', 0)
        if category == "balance":
            val_str = f"{int(val):,} Еж."
        elif category == "elephant_skin":
            val_str = f"{int(val):,} 🐘"
        elif category == "diamonds":
            val_str = f"{int(val):,} 💎"
        elif category == "total_feedings":
            val_str = f"{int(val):,} 🍖"
        elif category == "referrals_count":
            val_str = f"{int(val):,} 👬"
        else:
            val_str = f"{int(val):,}"
        list_html += f"""
        <li class="top-item">
            <span class="top-medal">{medal}</span>
            <div class="top-info">
                <div class="top-name">{cls_icon} {u.get('hedgehog_name', '?')} #{u.get('player_number', 0):04d}</div>
            </div>
            <span class="top-val">{val_str}</span>
        </li>"""
    if not top_users:
        list_html += '<li class="top-item" style="justify-content:center;color:rgba(255,255,255,0.3)">Пока никого нет</li>'
    list_html += '</ul>'

    content = f"""
    <div class="card">
        <div class="section-title">🏆 Топы</div>
        {cat_html}
        {periods_html}
        {list_html}
    </div>"""

    html = render_page("🦔 Говорящий Ёж — Топы", "tops", content)
    return web.Response(text=html, content_type='text/html')


# --- Кастомизация ---

async def handle_customize(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    msg = request.query.get('msg', '')
    msg_html = ""
    if msg == "name_ok":
        msg_html = '<div class="success-msg">✅ Имя изменено!</div>'
    elif msg == "color_ok":
        msg_html = '<div class="success-msg">✅ Цвет изменён! Списано 100 Ежидзиков</div>'
    elif msg == "color_no_money":
        msg_html = '<div class="error-msg" style="display:block">❌ Недостаточно Ежидзиков! Нужно 100</div>'
    elif msg == "class_ok":
        msg_html = '<div class="success-msg">✅ Класс куплен! Ёж возрождён!</div>'
    elif msg == "class_no_money":
        msg_html = '<div class="error-msg" style="display:block">❌ Недостаточно Ежидзиков!</div>'
    elif msg == "class_alive":
        msg_html = '<div class="error-msg" style="display:block">❌ Нельзя сменить класс живого ежа! Сначала продайте или отправьте на хранение.</div>'

    current_name = user_data.get('hedgehog_name', '🦔Ежъ🦔')
    current_color = user_data.get('hedgehog_color', 'Не выбран')
    current_cls = user_data.get('hedgehog_class', 'normal')
    status = user_data.get('status', 'alive')

    # Цвета
    colors_html = '<div class="color-grid">'
    for ckey, cname in COLORS.items():
        current = ' current' if ckey == current_color else ''
        colors_html += f'<a href="/customize/color/{ckey}" class="color-btn{current}">{cname}</a>'
    colors_html += '</div>'

    # Классы
    classes_html = ""
    for cls_key, cls_data in CLASSES.items():
        is_current = cls_key == current_cls
        if is_current:
            classes_html += f"""
            <div class="deposit-card" style="border-color:rgba(120,50,255,0.4)">
                <div class="deposit-type">{cls_data['name']} <span style="font-size:12px;color:#a78bfa">Текущий</span></div>
                <div class="deposit-info">Макс. сытость: {cls_data['max_satiety']}%</div>
            </div>"""
        else:
            can_buy = status != 'alive' and user_data.get('balance', 0) >= cls_data['price']
            btn_class = "btn-green btn-sm" if can_buy else "btn-sm"
            style = 'style="opacity:0.5"' if status == 'alive' else ''
            buy_html = f'<a href="/customize/buy_class/{cls_key}" class="{btn_class} btn" {style}>Купить за {cls_data["price"]} Еж.</a>' if status != 'alive' else '<span style="font-size:12px;color:rgba(255,255,255,0.3)">Ёж должен быть мёртв/продан</span>'
            classes_html += f"""
            <div class="deposit-card">
                <div class="deposit-type">{cls_data['name']}</div>
                <div class="deposit-info">Цена: {cls_data['price']} Еж. &bull; Макс. сытость: {cls_data['max_satiety']}%</div>
                <div style="margin-top:8px">{buy_html}</div>
            </div>"""

    content = f"""
    {msg_html}
    <div class="card">
        <div class="section-title">✏️ Имя ежа</div>
        <form method="POST" action="/customize/name">
            <div class="input-group">
                <input type="text" name="name" value="{current_name}" maxlength="50" required>
            </div>
            <button type="submit" class="btn btn-primary btn-sm">Сохранить</button>
        </form>
    </div>
    <div class="card">
        <div class="section-title">🎨 Цвет иголок</div>
        <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:12px">Смена цвета стоит 100 Ежидзиков</p>
        <p style="font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:12px">Текущий: {COLORS.get(current_color, current_color)}</p>
        {colors_html}
    </div>
    <div class="card">
        <div class="section-title">🦔 Класс ежа</div>
        <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:12px">Покупка класса доступна когда ёж мёртв или продан</p>
        {classes_html}
    </div>"""

    html = render_page("🦔 Говорящий Ёж — Кастомизация", "customize", content)
    return web.Response(text=html, content_type='text/html')


async def handle_customize_name(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    new_name = str(data.get('name', '')).strip()[:50]
    if new_name:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET hedgehog_name = ? WHERE user_id = ?", (new_name, user_id))
            await db.commit()
    return web.HTTPFound('/customize?msg=name_ok')


async def handle_customize_color(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    color_id = request.match_info['color']
    if color_id not in COLORS:
        return web.HTTPFound('/customize')

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET balance = balance - 100, hedgehog_color = ? WHERE user_id = ? AND balance >= 100",
            (color_id, user_id)
        )
        await db.commit()
        if cursor.rowcount == 0:
            return web.HTTPFound('/customize?msg=color_no_money')
    return web.HTTPFound('/customize?msg=color_ok')


async def handle_customize_buy_class(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    cls_key = request.match_info['cls']
    if cls_key not in CLASSES:
        return web.HTTPFound('/customize')

    cls_data = CLASSES[cls_key]

    # Обновляем данные (могли измениться)
    user_data = await get_user_data(user_id)
    if user_data.get('status') == 'alive':
        return web.HTTPFound('/customize?msg=class_alive')
    if user_data.get('balance', 0) < cls_data['price']:
        return web.HTTPFound('/customize?msg=class_no_money')

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """UPDATE users SET balance = balance - ?, hedgehog_color = 'Не выбран',
               hedgehog_class = ?, happiness = 0, satiety = ?, status = 'alive', alert_sent = 0
               WHERE user_id = ? AND balance >= ?""",
            (cls_data['price'], cls_key, cls_data['max_satiety'], user_id, cls_data['price'])
        )
        await db.commit()
    return web.HTTPFound('/customize?msg=class_ok')


# --- Ежедневный бонус ---

async def handle_bonus(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    bonus_amount = int(await get_setting("daily_bonus", "25"))
    last_daily = user_data.get('last_daily')
    can_claim = True
    timer_text = ""

    if last_daily:
        try:
            last_dt = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S")
            diff = datetime.now() - last_dt
            if diff < timedelta(hours=24):
                can_claim = False
                remaining = timedelta(hours=24) - diff
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                timer_text = f"⏰ Следующий бонус через {hours}ч {minutes}мин"
        except:
            pass

    msg = request.query.get('msg', '')
    msg_html = ""
    if msg == "ok":
        msg_html = f'<div class="success-msg">✅ Получено {bonus_amount} Ежидзиков!</div>'

    if can_claim:
        bonus_html = f"""
        <div class="card bonus-card">
            <div class="bonus-amount">+{bonus_amount}</div>
            <div style="color:rgba(255,255,255,0.5);margin-top:4px">Ежидзиков 👍</div>
            <form method="POST" action="/bonus/claim" style="margin-top:20px">
                <button type="submit" class="btn btn-green">🎁 Забрать бонус</button>
            </form>
        </div>"""
    else:
        bonus_html = f"""
        <div class="card bonus-card">
            <div style="font-size:48px">⏳</div>
            <div class="bonus-timer">{timer_text}</div>
            <p style="color:rgba(255,255,255,0.4);margin-top:12px;font-size:14px">Бонус уже собран. Приходите позже!</p>
        </div>"""

    balance = user_data.get('balance', 0)
    content = f"""
    {msg_html}
    {bonus_html}
    <div class="card">
        <div class="section-title">Ваш баланс</div>
        <div class="stat-row">
            <span class="stat-label">👍 Ежидзики</span>
            <span class="stat-value gold">{balance:,}</span>
        </div>
    </div>"""

    html = render_page("🦔 Говорящий Ёж — Бонус", "bonus", content)
    return web.Response(text=html, content_type='text/html')


async def handle_bonus_claim(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    bonus_amount = int(await get_setting("daily_bonus", "25"))
    last_daily = user_data.get('last_daily')

    if last_daily:
        try:
            last_dt = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last_dt < timedelta(hours=24):
                return web.HTTPFound('/bonus')
        except:
            pass

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?",
                         (bonus_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        await db.commit()

    return web.HTTPFound('/bonus?msg=ok')


# --- Обменник ---

async def handle_exchange(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    tab = request.query.get('tab', 'skin')
    msg = request.query.get('msg', '')
    msg_html = ""
    if msg == "ok":
        msg_html = '<div class="success-msg">✅ Обмен выполнен!</div>'
    elif msg == "no_money":
        msg_html = '<div class="error-msg" style="display:block">❌ Недостаточно средств!</div>'
    elif msg == "invalid":
        msg_html = '<div class="error-msg" style="display:block">❌ Неверная сумма!</div>'

    balance = user_data.get('balance', 0)
    elephant_skin = user_data.get('elephant_skin', 0)
    diamonds = user_data.get('diamonds', 0)

    # Вкладки
    tabs_html = f"""
    <div class="exchange-direction">
        <a href="/exchange?tab=skin" class="{'active' if tab == 'skin' else ''}">🐘 Кожа</a>
        <a href="/exchange?tab=diamond" class="{'active' if tab == 'diamond' else ''}">💎 Алмазы</a>
        <a href="/exchange?tab=b1tcoin" class="{'active' if tab == 'b1tcoin' else ''}">⛏️ бNтk0ины</a>
    </div>"""

    if tab == "skin":
        form_html = f"""
        <div class="exchange-rate">⚡ Курс: 45 Ежидзиков = 1 Кожа слона &bull; 1 Кожа = 45 Ежидзиков</div>
        <div class="card">
            <div class="section-title">Ежидзики → Кожа слона</div>
            <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:10px">Купите кожу слона за Ежидзики</p>
            <form method="POST" action="/exchange/skin_to_balance">
                <div class="input-group">
                    <label>Количество кож для покупки</label>
                    <input type="number" name="amount" min="1" max="{balance // 45}" value="1" required>
                </div>
                <p style="font-size:12px;color:rgba(255,255,255,0.3);margin-bottom:8px">Списано: <span id="skin_cost">45</span> Ежидзиков</p>
                <button type="submit" class="btn btn-blue btn-sm">🐘 Купить кожу</button>
            </form>
        </div>
        <div class="card">
            <div class="section-title">Кожа слона → Ежидзики</div>
            <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:10px">Продайте кожу слона за Ежидзики</p>
            <form method="POST" action="/exchange/balance_to_skin">
                <div class="input-group">
                    <label>Количество кож для продажи</label>
                    <input type="number" name="amount" min="1" max="{elephant_skin}" value="1" required>
                </div>
                <p style="font-size:12px;color:rgba(255,255,255,0.3);margin-bottom:8px">Получите: <span id="skin_reward">45</span> Ежидзиков</p>
                <button type="submit" class="btn btn-green btn-sm">👍 Продать кожу</button>
            </form>
        </div>"""

    elif tab == "diamond":
        form_html = f"""
        <div class="exchange-rate">⚡ Курс: 3 Кожи слона = 1 Алмаз &bull; 1 Алмаз = 3 Кожи слона</div>
        <div class="card">
            <div class="section-title">Кожа → Алмазы</div>
            <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:10px">Обменяйте 3 кожи на 1 алмаз</p>
            <form method="POST" action="/exchange/skin_to_dia">
                <div class="input-group">
                    <label>Количество алмазов</label>
                    <input type="number" name="amount" min="1" max="{elephant_skin // 3}" value="1" required>
                </div>
                <p style="font-size:12px;color:rgba(255,255,255,0.3);margin-bottom:8px">Списано: 3 алмаза = 9 кож</p>
                <button type="submit" class="btn btn-sm" style="background:linear-gradient(135deg,#ec4899,#be185d);color:#fff">💎 Купить алмазы</button>
            </form>
        </div>
        <div class="card">
            <div class="section-title">Алмазы → Кожа</div>
            <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:10px">Обменяйте 1 алмаз на 3 кожи</p>
            <form method="POST" action="/exchange/dia_to_skin">
                <div class="input-group">
                    <label>Количество алмазов</label>
                    <input type="number" name="amount" min="1" max="{diamonds}" value="1" required>
                </div>
                <button type="submit" class="btn btn-blue btn-sm">🐘 Продать алмазы</button>
            </form>
        </div>"""

    else:  # b1tcoin
        rate = await get_b1tcoin_rate()
        diamond_rate = rate / 135
        m1ning = await get_m1ning_data(user_id)
        b1tcoins = m1ning.get('b1tcoins', 0)

        form_html = f"""
        <div class="exchange-rate">⚡ Курс: 1 бNтk0ин = {rate:.2f} Ежидзиков &bull; 1 Алмаз ≈ {diamond_rate:.4f} бNтk0инов &bull; Комиссия 10%</div>
        <div class="card">
            <div class="section-title">бNтk0ины → Ежидзики</div>
            <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:10px">Обмен с комиссией 10%. У вас: {b1tcoins:.2f} бNтk0инов</p>
            <form method="POST" action="/exchange/b1tcoin_to_balance">
                <div class="input-group">
                    <label>Количество бNтk0инов</label>
                    <input type="number" name="amount" min="1" max="{int(b1tcoins)}" step="0.01" value="1" required>
                </div>
                <button type="submit" class="btn btn-green btn-sm">👍 Обменять</button>
            </form>
        </div>
        <div class="card">
            <div class="section-title">бNтk0ины → Алмазы</div>
            <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:10px">Обмен с комиссией 10%. У вас: {b1tcoins:.2f} бNтk0инов</p>
            <form method="POST" action="/exchange/b1tcoin_to_dia">
                <div class="input-group">
                    <label>Количество бNтk0инов</label>
                    <input type="number" name="amount" min="1" max="{int(b1tcoins)}" step="0.01" value="1" required>
                </div>
                <button type="submit" class="btn btn-sm" style="background:linear-gradient(135deg,#ec4899,#be185d);color:#fff">💎 Обменять</button>
            </form>
        </div>"""

    content = f"""
    <div class="card">
        <div class="section-title">Ваши средства</div>
        <div class="stat-row">
            <span class="stat-label">👍 Ежидзики</span>
            <span class="stat-value gold">{balance:,}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">🐘 Кожа слона</span>
            <span class="stat-value blue">{elephant_skin:,}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">💎 Алмазы</span>
            <span class="stat-value pink">{diamonds:,}</span>
        </div>
    </div>
    {msg_html}
    {tabs_html}
    {form_html}"""

    html = render_page("🦔 Говорящий Ёж — Обменник", "exchange", content)
    return web.Response(text=html, content_type='text/html')


# --- Обменник: обработчики POST ---

async def handle_exchange_skin_to_balance(request):
    """Ежидзики → Кожа слона"""
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    try:
        amount = int(data.get('amount', 0))
        if amount < 1:
            raise ValueError
    except (ValueError, TypeError):
        return web.HTTPFound('/exchange?tab=skin&msg=invalid')

    cost = amount * 45
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET balance = balance - ?, elephant_skin = elephant_skin + ? WHERE user_id = ? AND balance >= ?",
            (cost, amount, user_id, cost)
        )
        await db.commit()
        if cursor.rowcount == 0:
            return web.HTTPFound('/exchange?tab=skin&msg=no_money')
    return web.HTTPFound('/exchange?tab=skin&msg=ok')


async def handle_exchange_balance_to_skin(request):
    """Кожа слона → Ежидзики"""
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    try:
        amount = int(data.get('amount', 0))
        if amount < 1:
            raise ValueError
    except (ValueError, TypeError):
        return web.HTTPFound('/exchange?tab=skin&msg=invalid')

    reward = amount * 45
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET elephant_skin = elephant_skin - ?, balance = balance + ? WHERE user_id = ? AND elephant_skin >= ?",
            (amount, reward, user_id, amount)
        )
        await db.commit()
        if cursor.rowcount == 0:
            return web.HTTPFound('/exchange?tab=skin&msg=no_money')
    return web.HTTPFound('/exchange?tab=skin&msg=ok')


async def handle_exchange_skin_to_dia(request):
    """Кожа → Алмазы (3:1)"""
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    try:
        amount = int(data.get('amount', 0))
        if amount < 1:
            raise ValueError
    except (ValueError, TypeError):
        return web.HTTPFound('/exchange?tab=diamond&msg=invalid')

    skin_cost = amount * 3
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET elephant_skin = elephant_skin - ?, diamonds = diamonds + ? WHERE user_id = ? AND elephant_skin >= ?",
            (skin_cost, amount, user_id, skin_cost)
        )
        await db.commit()
        if cursor.rowcount == 0:
            return web.HTTPFound('/exchange?tab=diamond&msg=no_money')
    return web.HTTPFound('/exchange?tab=diamond&msg=ok')


async def handle_exchange_dia_to_skin(request):
    """Алмазы → Кожа (1:3)"""
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    try:
        amount = int(data.get('amount', 0))
        if amount < 1:
            raise ValueError
    except (ValueError, TypeError):
        return web.HTTPFound('/exchange?tab=diamond&msg=invalid')

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET diamonds = diamonds - ?, elephant_skin = elephant_skin + ? WHERE user_id = ? AND diamonds >= ?",
            (amount, amount * 3, user_id, amount)
        )
        await db.commit()
        if cursor.rowcount == 0:
            return web.HTTPFound('/exchange?tab=diamond&msg=no_money')
    return web.HTTPFound('/exchange?tab=diamond&msg=ok')


async def handle_exchange_b1tcoin_to_balance(request):
    """бNтk0ины → Ежидзики (10% комиссия)"""
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    try:
        amount = float(data.get('amount', 0))
        if amount < 1:
            raise ValueError
    except (ValueError, TypeError):
        return web.HTTPFound('/exchange?tab=b1tcoin&msg=invalid')

    rate = await get_b1tcoin_rate()
    commission = amount * 0.10
    net = amount - commission
    reward = round(net * rate)
    if reward <= 0:
        return web.HTTPFound('/exchange?tab=b1tcoin&msg=invalid')

    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем достаточно ли бNтk0инов
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT b1tcoins FROM m1ning_state WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                return web.HTTPFound('/exchange?tab=b1tcoin&msg=no_money')
        await db.execute("UPDATE m1ning_state SET b1tcoins = b1tcoins - ?, total_mined = total_mined WHERE user_id = ?",
                         (amount, user_id))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
        await db.commit()
    return web.HTTPFound('/exchange?tab=b1tcoin&msg=ok')


async def handle_exchange_b1tcoin_to_dia(request):
    """бNтk0ины → Алмазы (10% комиссия)"""
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    try:
        amount = float(data.get('amount', 0))
        if amount < 1:
            raise ValueError
    except (ValueError, TypeError):
        return web.HTTPFound('/exchange?tab=b1tcoin&msg=invalid')

    rate = await get_b1tcoin_rate()
    diamond_rate = rate / 135
    commission = amount * 0.10
    net = amount - commission
    reward = round(net * diamond_rate)
    if reward <= 0:
        return web.HTTPFound('/exchange?tab=b1tcoin&msg=invalid')

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT b1tcoins FROM m1ning_state WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < amount:
                return web.HTTPFound('/exchange?tab=b1tcoin&msg=no_money')
        await db.execute("UPDATE m1ning_state SET b1tcoins = b1tcoins - ?, total_mined = total_mined WHERE user_id = ?",
                         (amount, user_id))
        await db.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (reward, user_id))
        await db.commit()
    return web.HTTPFound('/exchange?tab=b1tcoin&msg=ok')


# --- Перевод ---

async def handle_transfer(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    msg = request.query.get('msg', '')
    msg_html = ""
    if msg == "ok":
        msg_html = '<div class="success-msg">✅ Перевод выполнен!</div>'
    elif msg == "no_money":
        msg_html = '<div class="error-msg" style="display:block">❌ Недостаточно средств!</div>'
    elif msg == "not_found":
        msg_html = '<div class="error-msg" style="display:block">❌ Игрок не найден!</div>'
    elif msg == "self":
        msg_html = '<div class="error-msg" style="display:block">❌ Нельзя перевести самому себе!</div>'
    elif msg == "invalid":
        msg_html = '<div class="error-msg" style="display:block">❌ Неверная сумма! Минимум 10 Ежидзиков</div>'

    balance = user_data.get('balance', 0)

    content = f"""
    {msg_html}
    <div class="card">
        <div class="section-title">💸 Перевод игроку</div>
        <p style="font-size:13px;color:rgba(255,255,255,0.4);margin-bottom:14px">Комиссия: 5% (минимум 1 Ежидзик). Минимальная сумма: 10</p>
        <form method="POST" action="/transfer/do">
            <div class="input-group">
                <label>Получатель (ID, @username или #номер)</label>
                <input type="text" name="recipient" placeholder="@user, 123456 или #0001" required>
            </div>
            <div class="input-group">
                <label>Сумма (Ежидзиков)</label>
                <input type="number" name="amount" min="10" max="{balance}" value="10" required>
            </div>
            <button type="submit" class="btn btn-primary">💸 Перевести</button>
        </form>
    </div>
    <div class="card">
        <div class="section-title">Ваш баланс</div>
        <div class="stat-row">
            <span class="stat-label">👍 Ежидзики</span>
            <span class="stat-value gold">{balance:,}</span>
        </div>
    </div>"""

    html = render_page("🦔 Говорящий Ёж — Перевод", "transfer", content)
    return web.Response(text=html, content_type='text/html')


async def handle_transfer_do(request):
    user_id, user_data = await _get_auth_user(request)
    if not user_id:
        return web.HTTPFound('/')

    data = await request.post()
    recipient_query = str(data.get('recipient', '')).strip()
    try:
        amount = int(data.get('amount', 0))
        if amount < 10:
            raise ValueError
    except (ValueError, TypeError):
        return web.HTTPFound('/transfer?msg=invalid')

    # Ищем получателя
    recipient = await find_user_flexible(recipient_query)
    if not recipient:
        return web.HTTPFound('/transfer?msg=not_found')

    recipient_id = recipient['user_id']
    if recipient_id == user_id:
        return web.HTTPFound('/transfer?msg=self')

    commission = max(1, int(amount * 0.05))
    to_receive = amount - commission

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
            (amount, user_id, amount)
        )
        await db.commit()
        if cursor.rowcount == 0:
            return web.HTTPFound('/transfer?msg=no_money')

        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (to_receive, recipient_id))
        await db.commit()

    return web.HTTPFound('/transfer?msg=ok')


# =====================================
# 🚀 ЗАПУСК WEB-СЕРВЕРА
# =====================================

async def handle_inline_image(request):
    """Отдаёт сгенерированную inline-картинку из /tmp/ezh_inline/"""
    filename = request.match_info.get('filename', '')
    filepath = f"/tmp/ezh_inline/{filename}"
    if os.path.exists(filepath) and filename.endswith('.png'):
        return web.FileResponse(filepath, headers={'Cache-Control': 'public, max-age=300'})
    return web.Response(status=404, text="Not found")


async def start_web_server():
    global PUBLIC_URL
    app = web.Application()

    # Логин / выход
    app.router.add_get('/', handle_index)
    app.router.add_get('/login', handle_login)
    app.router.add_post('/login', handle_login)
    app.router.add_post('/logout', handle_logout)

    # Основные страницы
    app.router.add_get('/hedgehog', handle_hedgehog)
    app.router.add_get('/finances', handle_finances)
    app.router.add_get('/tops', handle_tops)
    app.router.add_get('/customize', handle_customize)
    app.router.add_get('/bonus', handle_bonus)
    app.router.add_get('/exchange', handle_exchange)
    app.router.add_get('/transfer', handle_transfer)

    # POST действия
    app.router.add_post('/customize/name', handle_customize_name)
    app.router.add_get('/customize/color/{color}', handle_customize_color)
    app.router.add_get('/customize/buy_class/{cls}', handle_customize_buy_class)
    app.router.add_post('/bonus/claim', handle_bonus_claim)

    # Обменник POST
    app.router.add_post('/exchange/skin_to_balance', handle_exchange_skin_to_balance)
    app.router.add_post('/exchange/balance_to_skin', handle_exchange_balance_to_skin)
    app.router.add_post('/exchange/skin_to_dia', handle_exchange_skin_to_dia)
    app.router.add_post('/exchange/dia_to_skin', handle_exchange_dia_to_skin)
    app.router.add_post('/exchange/b1tcoin_to_balance', handle_exchange_b1tcoin_to_balance)
    app.router.add_post('/exchange/b1tcoin_to_dia', handle_exchange_b1tcoin_to_dia)

    # Перевод POST
    app.router.add_post('/transfer/do', handle_transfer_do)

    # Inline-картинки
    app.router.add_get('/img/{filename}', handle_inline_image)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print(f"🌐 Web-сервер запущен на порту 8080 → {PUBLIC_URL}")
