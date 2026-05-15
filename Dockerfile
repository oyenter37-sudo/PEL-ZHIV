FROM python:3.11-slim

WORKDIR /app

# Системные зависимости для Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и ставим их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY Bot.py .

# Том для базы данных (чтобы не терять данные при пересоздании контейнера)
VOLUME /app/data

# Переменные окружения
ENV BOT_TOKEN=""
ENV DB_NAME="/app/data/hedgehog_bot.db"

CMD ["python", "Bot.py"]
