FROM python:3.11-slim

WORKDIR /app

# Ключевое: чтобы видеть print() и ошибки в логах контейнера в реальном времени
ENV PYTHONUNBUFFERED=1

# Системные зависимости для Pillow + шрифты для кириллицы (Image Test)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и ставим их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY Bot.py .
COPY web.py .
COPY navalnyy.py .

# Копируем базу данных
COPY hedgehog_bot.db .

CMD ["python", "Bot.py"]
