# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - WEB INTERFACE v5 🦔
# =====================================
# Веб-интерфейс для Telegram-бота
# Запускается параллельно с ботом на порту 8080

import os
import json
import secrets
import asyncio
import subprocess
import re
from datetime import datetime, timedelta

import aiosqlite
from aiohttp import web

DB_NAME = os.environ.get("DB_NAME", "hedgehog_bot.db")

# Глобальная переменная с публичным URL
PUBLIC_URL = None

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

    /* Анимированный фон */
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

    /* Карточки */
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

    /* Заголовок */
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

    /* Навигация */
    .nav {
        display: flex;
        gap: 10px;
        margin-bottom: 16px;
    }
    .nav a {
        flex: 1;
        text-align: center;
        padding: 12px 8px;
        border-radius: 14px;
        text-decoration: none;
        font-weight: 600;
        font-size: 14px;
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

    /* Стат строки */
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

    /* Прогресс-бар */
    .progress-wrap {
        margin-top: 4px;
    }
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

    /* Секция заголовок */
    .section-title {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: rgba(255,255,255,0.35);
        margin: 20px 0 10px;
        padding-left: 4px;
    }

    /* Вклады */
    .deposit-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .deposit-type {
        font-weight: 700;
        font-size: 15px;
        margin-bottom: 6px;
    }
    .deposit-info {
        font-size: 13px;
        color: rgba(255,255,255,0.5);
    }

    /* Логин форма */
    .login-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }
    .login-card {
        width: 100%;
        max-width: 400px;
    }
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
    .input-group {
        margin-bottom: 16px;
    }
    .input-group input {
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
    .input-group input:focus {
        border-color: rgba(120,50,255,0.5);
        box-shadow: 0 0 20px rgba(120,50,255,0.15);
    }
    .input-group input::placeholder {
        color: rgba(255,255,255,0.3);
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
    }

    /* Статус бейдж */
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

    /* Ёжик анимация */
    .hedgehog-icon {
        font-size: 48px;
        text-align: center;
        animation: bounce 2s ease-in-out infinite;
    }
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
    }

    /* Адаптив */
    @media (max-width: 500px) {
        .container { padding: 12px; }
        .card { padding: 18px; border-radius: 16px; }
        .header h1 { font-size: 24px; }
    }
    """


def render_login(error: str = ""):
    err_style = 'style="display:block"' if error else ''
    err_text = f"Неверный ключ входа" if error else ""
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


def render_dashboard(user_data: dict, bank_deposits: list, section: str = "hedgehog"):
    # Расчёты
    join_date = user_data.get('join_date', '')
    days_in_bot = 0
    if join_date:
        try:
            jd = datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
            days_in_bot = (datetime.now() - jd).days
        except:
            pass

    satiety = user_data.get('satiety', 100)
    satiety_int = int(satiety)
    if satiety_int > 60:
        sat_class = "green"
    elif satiety_int > 25:
        sat_class = "yellow"
    else:
        sat_class = "red"

    status = user_data.get('status', 'alive')
    status_badge = f'<span class="badge badge-alive">Жив</span>' if status == 'alive' else '<span class="badge badge-dead">Мёртв</span>'

    cls_map = {
        "normal": "Обычный Еж 🦔",
        "ejidze": "Ежидзе 🤠",
        "fat": "Толстый Еж 🦔",
        "golden": "Золотой Еж 🟡",
    }
    cls_name = cls_map.get(user_data.get('hedgehog_class', 'normal'), 'Неизвестно')

    color_map = {
        "black": "⚫ Чёрный", "brown": "🟤 Коричневый", "white": "⚪ Белый",
        "orange": "🟠 Оранжевый", "gold": "🟡 Золотой", "blue": "🔵 Синий",
        "purple": "🟣 Фиолетовый", "red": "🔴 Красный", "green": "🟢 Зелёный",
        "rainbow": "🌈 Радужный", "Не выбран": "Не выбран",
    }
    color_name = color_map.get(user_data.get('hedgehog_color', 'Не выбран'), user_data.get('hedgehog_color', 'Не выбран'))

    # --- Секция Мой Ёж ---
    hedgehog_section = f"""
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
            <span class="stat-value {'green' if satiety_int > 60 else 'red' if satiety_int < 25 else 'gold'}">{satiety_int}%</span>
        </div>
        <div class="progress-wrap">
            <div class="progress-bar">
                <div class="progress-fill {sat_class}" style="width:{min(satiety_int, 100)}%"></div>
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
    </div>
    """

    # --- Секция Финансы ---
    # Вклады
    deposits_html = ""
    for dep in bank_deposits:
        dep_type_names = {
            "demand": "📦 До востребования",
            "stable": "🏦 Стабильный",
            "premium": "👑 Премиум",
        }
        dep_rates = {"demand": "0.5%", "stable": "1.2%", "premium": "2.0%"}
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
                    unlock_text = f" &bull; 🔒 Заморожен ещё {hours}ч {mins}м"
                else:
                    unlock_text = " &bull; ✅ Разблокирован"
            except:
                pass

        deposits_html += f"""
        <div class="deposit-card">
            <div class="deposit-type">{dname} <span style="font-size:12px;color:rgba(255,255,255,0.4)">{drate}/день</span></div>
            <div class="deposit-info">
                💰 Вклад: {dep['amount']} Еж. &bull; 📈 Начислено: {dep['accrued']} Еж.{unlock_text}
            </div>
        </div>
        """

    if not deposits_html:
        deposits_html = '<div style="text-align:center;color:rgba(255,255,255,0.3);padding:20px">Нет активных вкладов</div>'

    casino_profit = user_data.get('total_casino_profit', 0)
    casino_profit_color = "green" if casino_profit >= 0 else "red"
    casino_profit_sign = "+" if casino_profit >= 0 else ""

    finances_section = f"""
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
            <span class="stat-label">📊 Итого профит</span>
            <span class="stat-value {casino_profit_color}">{casino_profit_sign}{casino_profit:,} Еж.</span>
        </div>
    </div>

    <div class="card">
        <div class="section-title">🏦 Вклады в банке</div>
        {deposits_html}
    </div>
    """

    # Выбор секции
    content = hedgehog_section if section == "hedgehog" else finances_section

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🦔 Говорящий Ёж — Панель</title>
    <style>{get_base_css()}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🦔 Говорящий Ёж</h1>
        <div class="subtitle">Личный кабинет</div>
    </div>

    <div class="nav">
        <a href="/hedgehog" class="{'active' if section == 'hedgehog' else ''}">🦔 Мой Ёж</a>
        <a href="/finances" class="{'active' if section == 'finances' else ''}">🌟 Финансы</a>
    </div>

    {content}

    <form method="POST" action="/logout">
        <button type="submit" class="btn btn-logout">Выйти</button>
    </form>
</div>
</body>
</html>"""


# =====================================
# 🔐 РАБОТА С КЛЮЧАМИ
# =====================================

async def generate_web_key(user_id: int) -> str:
    """Генерирует ключ входа для пользователя. Один ключ на юзера, старый удаляется."""
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
    """Проверяет ключ и возвращает user_id или None. Ключ живёт 1 час."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM web_keys WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            # Проверяем срок
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
    """Получает данные пользователя из БД."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def get_bank_deposits(user_id: int) -> list:
    """Получает активные вклады пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bank_deposits WHERE user_id = ? AND status = 'active'",
            (user_id,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


# =====================================
# 🌐 ОБРАБОТЧИКИ ЗАПРОСОВ
# =====================================

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

    # Успешный вход
    resp = web.HTTPFound('/hedgehog')
    resp.set_cookie('session_key', key, max_age=3600, httponly=True)
    return resp


async def handle_logout(request):
    session_key = request.cookies.get('session_key', '')
    # Удаляем ключ
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM web_keys WHERE key = ?", (session_key,))
        await db.commit()
    resp = web.HTTPFound('/')
    resp.del_cookie('session_key')
    return resp


async def handle_hedgehog(request):
    session_key = request.cookies.get('session_key', '')
    user_id = await validate_web_key(session_key)
    if not user_id:
        return web.HTTPFound('/')

    user_data = await get_user_data(user_id)
    if not user_data:
        return web.HTTPFound('/')

    bank_deposits = await get_bank_deposits(user_id)
    html = render_dashboard(user_data, bank_deposits, section="hedgehog")
    return web.Response(text=html, content_type='text/html')


async def handle_finances(request):
    session_key = request.cookies.get('session_key', '')
    user_id = await validate_web_key(session_key)
    if not user_id:
        return web.HTTPFound('/')

    user_data = await get_user_data(user_id)
    if not user_data:
        return web.HTTPFound('/')

    bank_deposits = await get_bank_deposits(user_id)
    html = render_dashboard(user_data, bank_deposits, section="finances")
    return web.Response(text=html, content_type='text/html')


# =====================================
# 🚀 ЗАПУСК WEB-СЕРВЕРА
# =====================================

async def start_web_server():
    global PUBLIC_URL
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/login', handle_login)
    app.router.add_post('/login', handle_login)
    app.router.add_post('/logout', handle_logout)
    app.router.add_get('/hedgehog', handle_hedgehog)
    app.router.add_get('/finances', handle_finances)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 Web-сервер запущен на порту 8080")

    # Запускаем cloudflared туннель
    await _start_cloudflare_tunnel()


async def _start_cloudflare_tunnel():
    """Запускает cloudflared quick tunnel для публичного доступа."""
    global PUBLIC_URL
    cloudflared_path = os.path.expanduser("~/.local/bin/cloudflared")
    if not os.path.exists(cloudflared_path):
        print("⚠️ cloudflared не найден, туннель не запущен")
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            cloudflared_path, "tunnel", "--url", "http://localhost:8080",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Читаем stderr чтобы вытащить URL
        url_found = None
        for _ in range(50):  # ждём до 25 секунд
            line = await asyncio.wait_for(proc.stderr.readline(), timeout=30)
            line = line.decode("utf-8", errors="ignore")
            match = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', line)
            if match:
                url_found = match.group(0)
                break

        if url_found:
            PUBLIC_URL = url_found
            print(f"🌐 Публичный URL: {PUBLIC_URL}")
        else:
            print("⚠️ Не удалось получить URL туннеля")
    except Exception as e:
        print(f"⚠️ Ошибка запуска cloudflared: {e}")
