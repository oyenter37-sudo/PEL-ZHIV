#!/usr/bin/env python3
# =====================================
# 🦔 ГОВОРЯЩИЙ ЕЖ - КОДИРОВЩИК ТОКЕНА 🦔
# =====================================
# Готовит base64-блоб для _BOT_TOKEN_B64 в Bot.py. Руками Bot.py править не
# нужно: получил токен у @BotFather -> прогнал сюда -> вставил вывод в Bot.py.
#
#   python encode_token.py                       # спросит токен скрытно
#   python encode_token.py "123456:AAxxxx"       # из аргумента (залезет в history!)
#   echo -n "123456:AAxxxx" | python encode_token.py -
#
# Флаги:
#   --split  разбить блоб строками по 60 символов (как выводит утилита base64)
#   --force  не проверять формат токена
#   --check "<токен>"  только сверить текущий блоб в Bot.py с токеном

import base64
import getpass
import os
import re
import sys

BOT_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Bot.py")

# Тот же формат, что проверяет Bot.py: "<id бота>:<хэш из 20-64 символов>"
SHAPE = re.compile(r"^\d{1,20}:[A-Za-z0-9_.-]{20,64}$")
BLOB_RE = re.compile(r"_BOT_TOKEN_B64\s*=\s*(\([^)]*\)|\"[^\n]*\")", re.S)


def read_blob_from_bot_py() -> str:
    """Вытаскивает текущий _BOT_TOKEN_B64 из Bot.py (нужно для --check)."""
    try:
        with open(BOT_PY, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as exc:
        sys.exit(f"❌ Не удалось прочитать {BOT_PY}: {exc}")
    match = BLOB_RE.search(src)
    if not match:
        sys.exit("❌ В Bot.py не нашёл _BOT_TOKEN_B64 — блок настроек переехал?")
    return "".join(re.findall(r'"([^"]*)"', match.group(1)))


def decode(blob: str) -> str:
    blob = "".join(blob.split())
    return base64.b64decode(blob + "=" * (-len(blob) % 4)).decode("utf-8").strip()


def wrap(text: str, width: int = 60):
    return [text[i:i + width] for i in range(0, len(text), width)]


def main() -> int:
    argv = sys.argv[1:]
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]

    if "--check" in flags:
        token = args[0].strip() if args else getpass.getpass("Токен для сверки: ").strip()
        try:
            current = decode(read_blob_from_bot_py())
        except Exception as exc:  # битый блоб в Bot.py
            print(f"❌ Текущий блоб в Bot.py не читается: {exc}", file=sys.stderr)
            return 1
        if token == current:
            print("✅ Совпадает: блоб в Bot.py — это именно этот токен.")
            return 0
        bot_id = current.split(":", 1)[0] if ":" in current else "???"
        print(f"❌ Не совпадает: в Bot.py зашит токен бота {bot_id} "
              f"(длина {len(current)}), а подставлен другой (длина {len(token)}).")
        return 1

    raw = args[0] if args else ""
    if raw == "-":
        raw = sys.stdin.readline()
    elif not raw:
        raw = getpass.getpass("Токен от @BotFather (вводимое не видно): ")
    else:
        print("⚠️  Токен в аргументе остаётся в history шелла — лучше без аргумента "
              "или через stdin: `... | python encode_token.py -`", file=sys.stderr)

    token = raw.strip()
    if not token:
        print("❌ Пусто — токен не получен.", file=sys.stderr)
        return 1
    if "--force" not in flags and not SHAPE.match(token):
        print(f"❌ Не похоже на токен Telegram: жду «<цифры>:<хэш 20-64 символа>», "
              f"а получил строку длиной {len(token)}.", file=sys.stderr)
        print("   Уверен, что это токен? Повтори с --force.", file=sys.stderr)
        return 1

    blob = base64.b64encode(token.encode("utf-8")).decode("ascii")
    parts = wrap(blob)
    if len(parts) == 1 or "--split" not in flags:
        literal = f'"{blob}"'
    else:
        literal = "(\n" + "".join(f'    "{p}"\n' for p in parts) + ")"

    print("\n// --- вставь в Bot.py вместо текущего _BOT_TOKEN_B64 --- //\n")
    print(f"_BOT_TOKEN_B64 = {literal}")

    ok = decode("".join(re.findall(r'"([^"]*)"', literal))) == token
    print("\n// --- самопроверка обратной сборки --- //")
    print(f"✅ блоб раскодировывается в тот же токен ({len(token)} символов)" if ok
          else "❌ блоб битый — не вставляй его в Bot.py")
    print("\nПомни: base64 — это не шифрование. На проде токен лучше держать в "
          "переменной окружения BOT_TOKEN (она приоритетнее блоба), а старый "
          "токен, который светился в git-истории, отозвать через @BotFather.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
