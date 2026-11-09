# -*- coding: utf-8 -*-
"""Пароли и сессии пользователей панели «Умной AI-Теплицы».

Модуль не обращается к базе: он только считает хеши и придумывает токены,
поэтому подходит и SQLite-, и PostgreSQL-бэкенду без изменений.

Формат хеша пароля: pbkdf2_sha256$<итерации>$<соль hex>$<хеш hex>.
Перебор медленный (200 000 итераций), соль у каждого пароля своя, поэтому
одной только утечки файла БД недостаточно, чтобы восстановить пароли.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import secrets
from typing import Dict, Optional, Tuple

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 200_000
SALT_BYTES = 16
TOKEN_BYTES = 32
SESSION_DAYS = 30
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 64
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 256
ROLES = ("admin", "user")
PUBLIC_FIELDS = ("id", "username", "role", "created_at")

# Профиль игрока. Поля необязательные: пустая строка значит «не заполнено»,
# и страница показывает логин. Аватар хранится картинкой в базе: так профиль
# переезжает вместе с дампом и не зависит от каталога файлов на сервере.
MAX_DISPLAY_NAME = 40
MAX_BIO = 280
AVATAR_MAX_BYTES = 512 * 1024
AVATAR_TYPES = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WebP"}
ACCENT_PATTERN = re.compile(r"^#[0-9a-f]{6}$")
# Ободки аватара: у каждой мини-игры витрины свой знак, плюс несколько общих.
# Это источник правды для сервера; те же идентификаторы рисуются на страницах
# (см. front/css/main.css, раздел «Персонализация профиля»).
FRAMES: Tuple[str, ...] = (
    "",                 # без ободка
    "narutodle",        # «Свиток Конохи» — спираль, оранжевый вихрь
    "animesongless",    # «Винил» — пластинка опенингов
    "csdraft",          # «87-0» — тактический зелёный с золотом
    "dota322",          # «322-0» — красно-чёрный вихрь
    "valorant",         # «13-0» — розовый с бирюзой
    "rl",               # «4-0» — синий с оранжевым
    "songguess",        # «Микрофон» — неоновый пурпур
    "raporder",         # «Золотая цепь» — металлическое золото
    "greenhouse",       # «Теплица» — зелёный с листом
    "legend",           # «Легенда» — переливающийся радужный ободок
    "admin",            # «Смотритель» — только администраторам
    "founder",          # «Основатель» — только администраторам
    "konoha",           # «Коноха» — награда за коллекцию персонажей
)

# Ободки, которые ставит только администратор: роль проверяет сервер.
ADMIN_FRAMES: Tuple[str, ...] = ("admin", "founder")

# Оформление карточки профиля (фон и рамка карточки).
CARDS: Tuple[str, ...] = (
    "",                 # обычная карточка
    "greenhouse",       # «Теплица» — зелёный градиент
    "neon",             # «Неон AmrGames» — тёмный фон со свечением
    "gold",             # «Золото» — премиальный отблеск
    "pixel",            # «Пиксели» — шахматка сеттинга игр
    "spotlight",        # «Прожектор» — радиальное свечение
    "crown",            # «Корона» — награда за победы в турнирах драфтов
    "architect",        # «Архитектор» — только администраторам
    "scroll",           # «Свиток» — награда за коллекцию персонажей
)

# Оформления, которые ставит только администратор.
ADMIN_CARDS: Tuple[str, ...] = ("architect",)

AVATAR_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/webp": (b"RIFF",),
}


def hash_password(password: str) -> str:
    """Возвращает хеш пароля вместе с солью и числом итераций."""
    if not password:
        raise ValueError("Пароль не может быть пустым")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: Optional[str]) -> bool:
    """Сравнивает пароль с сохранённым хешем; сравнение — за постоянное время."""
    if not password or not encoded:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        salt = bytes.fromhex(salt_hex)
        rounds = int(iterations)
    except (ValueError, TypeError):
        return False
    if rounds < 1:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(digest.hex(), digest_hex)


def new_token() -> str:
    """Случайный токен сессии (URL-safe, около 43 символов)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def normalize_username(username: str) -> str:
    """Логин без лишних пробелов: '  Admin ' и 'admin' — один и тот же аккаунт."""
    return (username or "").strip().lower()


def validate_username(username: str) -> str:
    """Проверяет логин при создании аккаунта и возвращает его в нормальном виде."""
    name = normalize_username(username)
    if len(name) < MIN_USERNAME_LENGTH:
        raise ValueError(f"Логин должен быть не короче {MIN_USERNAME_LENGTH} символов")
    if len(name) > MAX_USERNAME_LENGTH:
        raise ValueError(f"Логин должен быть не длиннее {MAX_USERNAME_LENGTH} символов")
    if any(ch.isspace() for ch in name):
        raise ValueError("Логин не может содержать пробелы")
    return name


def validate_password(password: str) -> str:
    """Проверяет пароль при создании аккаунта или смене пароля."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Пароль должен быть не длиннее {MAX_PASSWORD_LENGTH} символов")
    return password


def validate_role(role: str) -> str:
    value = (role or "user").strip().lower()
    if value not in ROLES:
        raise ValueError(f"Неизвестная роль: {role}")
    return value


def public_user(user: Dict[str, object]) -> Dict[str, object]:
    """Убирает хеш пароля из строки пользователя перед отдачей в JSON."""
    return {field: user.get(field) for field in PUBLIC_FIELDS}


def validate_display_name(value: object) -> str:
    """Имя в профиле: пробелы схлопываются, переводы строк не допускаются."""
    text = " ".join(str(value or "").split())
    if len(text) > MAX_DISPLAY_NAME:
        raise ValueError(f"Имя в профиле — не длиннее {MAX_DISPLAY_NAME} символов")
    if any(ord(ch) < 32 for ch in text):
        raise ValueError("Имя в профиле не может содержать управляющие символы")
    return text


def validate_bio(value: object) -> str:
    """О себе: простой текст, до 280 символов, без лишних пустых строк."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) > MAX_BIO:
        raise ValueError(f"Описание — не длиннее {MAX_BIO} символов")
    return text


def validate_accent(value: object) -> str:
    """Цвет профиля: пусто или #RRGGBB."""
    text = str(value or "").strip().lower()
    if text and not ACCENT_PATTERN.match(text):
        raise ValueError("Цвет указывается как #RRGGBB")
    return text


def validate_frame(value: object, role: str = "user") -> str:
    """Ободок аватара: идентификатор из списка FRAMES или пусто."""
    text = str(value or "").strip().lower()
    if text not in FRAMES:
        raise ValueError("Неизвестный ободок профиля")
    if text in ADMIN_FRAMES and role != "admin":
        raise ValueError("Этот ободок доступен только администратору")
    return text


def validate_card(value: object, role: str = "user") -> str:
    """Оформление карточки профиля: идентификатор из CARDS или пусто."""
    text = str(value or "").strip().lower()
    if text not in CARDS:
        raise ValueError("Неизвестное оформление карточки профиля")
    if text in ADMIN_CARDS and role != "admin":
        raise ValueError("Это оформление доступно только администратору")
    return text


def parse_avatar(value: object) -> Tuple[str, bytes]:
    """Разбирает картинку из data URL и проверяет тип, размер и сигнатуру.

    Клиент уменьшает фото до 256 px перед отправкой, поэтому даже снимок
    с телефона проходит: 512 КБ — запас на PNG с прозрачностью.
    """
    text = str(value or "").strip()
    header, _, payload = text.partition(",")
    if not header.startswith("data:image/") or not payload:
        raise ValueError("Нужна картинка, закодированная как data URL")
    mime = header[len("data:"):].split(";")[0].strip().lower()
    if mime not in AVATAR_TYPES:
        raise ValueError("Поддерживаются PNG, JPEG и WebP")
    if "base64" not in header:
        raise ValueError("Картинку нужно передать в base64")
    try:
        blob = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Не удалось прочитать картинку") from exc
    if not blob:
        raise ValueError("Картинка пустая")
    if len(blob) > AVATAR_MAX_BYTES:
        raise ValueError("Картинка больше 512 КБ — уменьшите её")
    if not blob.startswith(AVATAR_SIGNATURES[mime]):
        raise ValueError("Содержимое файла не похоже на картинку")
    return mime, blob


__all__ = [
    "SESSION_DAYS",
    "ROLES",
    "MAX_BIO",
    "MAX_DISPLAY_NAME",
    "FRAMES",
    "CARDS",
    "ADMIN_FRAMES",
    "ADMIN_CARDS",
    "hash_password",
    "verify_password",
    "new_token",
    "normalize_username",
    "validate_username",
    "validate_password",
    "validate_role",
    "validate_display_name",
    "validate_bio",
    "validate_accent",
    "validate_frame",
    "validate_card",
    "parse_avatar",
    "public_user",
]
