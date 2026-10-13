# -*- coding: utf-8 -*-
"""Пароли и сессии пользователей панели «Умной AI-Теплицы».

Модуль не обращается к базе: он только считает хеши и придумывает токены,
поэтому подходит и SQLite-, и PostgreSQL-бэкенду без изменений.

Формат хеша пароля: pbkdf2_sha256$<итерации>$<соль hex>$<хеш hex>.
Перебор медленный (200 000 итераций), соль у каждого пароля своя, поэтому
одной только утечки файла БД недостаточно, чтобы восстановить пароли.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Dict, Optional

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


__all__ = [
    "SESSION_DAYS",
    "ROLES",
    "hash_password",
    "verify_password",
    "new_token",
    "normalize_username",
    "validate_username",
    "validate_password",
    "validate_role",
    "public_user",
]
