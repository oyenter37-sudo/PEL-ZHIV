FROM python:3.11-slim

WORKDIR /app

# Ключевое: чтобы видеть print() и ошибки в логах контейнера в реальном времени
ENV PYTHONUNBUFFERED=1

# Системные зависимости для Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и ставим их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY Bot.py .

# Том для базы данных
VOLUME /app/data

CMD ["python", "Bot.py"]
