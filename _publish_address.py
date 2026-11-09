# -*- coding: utf-8 -*-
"""Публикация адреса API и ключа панели на сайте.

Поддомен быстрого туннеля (localhost.run) меняется при каждом перезапуске,
поэтому вбивать адрес руками после каждой перезагрузки не нужно: скрипт кладёт
текущий адрес из data/tunnel-url.txt в файл games/api-address.json на хостинге,
откуда его подхватывают панель и игры. Туда же попадает ключ панели, чтобы
браузеру не приходилось спрашивать его у пользователя.

Ключ берётся из переменной GH_API_KEY или из файла data/api-key.txt (каталог
data/ в репозиторий не попадает). Внимание: файл на сайте открыт всем, поэтому
ключ в нём сможет прочитать любой посетитель — публикуйте его, только если
доступ к панели не является секретом. Без ключа публикуется один адрес.

Что нужно: пароль хостинга в переменной окружения GH_HOST_PASSWORD (или в файле
data/host-password.txt) и установленный paramiko (см. backend/requirements.txt).

Примеры:
    python _publish_address.py                      # адрес из data/tunnel-url.txt
    python _publish_address.py --address https://abc.lhr.life
    python _publish_address.py --dry-run            # показать, что будет записано
    python _publish_address.py --no-key             # только адрес, без ключа
    python _publish_address.py --quiet              # для вызова из скрипта туннеля

Выход: 0 — опубликовано (или публиковать было нечего и это --quiet),
1 — ошибка публикации.
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL_FILE = ROOT / "data" / "tunnel-url.txt"
PASSWORD_FILE = ROOT / "data" / "host-password.txt"
KEY_FILE = ROOT / "data" / "api-key.txt"
FILE_NAME = "api-address.json"
RELATIVE_DIR = "games"
DEFAULT_DOMAINS = ("ai-parnik.ru", "ai-parnik.online")


def read_password() -> str:
    """Пароль хостинга: переменная окружения, иначе файл рядом с данными.

    Каталог data/ в репозиторий не попадает, поэтому пароль можно держать там:
    так адрес публикует и скрипт туннеля, которому переменные окружения не
    передаются.
    """
    value = os.environ.get("GH_HOST_PASSWORD", "").strip()
    if value:
        return value
    if PASSWORD_FILE.exists():
        return PASSWORD_FILE.read_text(encoding="utf-8-sig").strip()
    return ""


def read_address(explicit: str) -> str:
    if explicit:
        return explicit.strip().rstrip("/")
    if URL_FILE.exists():
        return URL_FILE.read_text(encoding="utf-8-sig").strip().rstrip("/")
    return ""


def read_api_key(explicit: str, publish: bool) -> str:
    """Ключ панели: переменная окружения, иначе файл рядом с данными.

    Файл на сайте открыт всем, поэтому ключ в нём — осознанный выбор: без
    data/api-key.txt и без GH_API_KEY публикуется один адрес.
    """
    if not publish:
        return ""
    if explicit:
        return explicit.strip()
    value = os.environ.get("GH_API_KEY", "").strip()
    if value:
        return value
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8-sig").strip()
    return ""


def build_document(address: str, api_key: str = "") -> bytes:
    payload = {
        "apiBase": address,
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    if api_key:
        payload["apiKey"] = api_key
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def upload(host: str, user: str, password: str, remote_base: str, domains: list[str],
           content: bytes, quiet: bool) -> int:
    import paramiko

    transport = paramiko.Transport((host, 22))
    transport.connect(username=user, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    failures = 0
    try:
        for domain in domains:
            remote_dir = posixpath.join(remote_base, domain, RELATIVE_DIR)
            try:
                sftp.stat(remote_dir)
            except IOError:
                failures += 1
                print(f"FAIL {domain}: нет каталога {remote_dir}")
                continue
            target = posixpath.join(remote_dir, FILE_NAME)
            with sftp.open(target, "wb") as handle:
                handle.write(content)
            written = sftp.open(target, "rb").read()
            same = written == content
            if not same:
                failures += 1
            if not quiet or not same:
                print(f"{'OK  ' if same else 'FAIL'} {domain}: {target} ({len(content)} байт)")
    finally:
        sftp.close()
        transport.close()
    return failures


def verify(domains: list[str], address: str, api_key: str, quiet: bool) -> int:
    """Читает файл с сайта по HTTPS: так видно и кэш, и права доступа."""
    failures = 0
    for domain in domains:
        url = f"https://{domain}/{RELATIVE_DIR}/{FILE_NAME}?v={int(datetime.now().timestamp())}"
        request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as error:
            failures += 1
            print(f"FAIL {domain}: файл не читается ({error})")
            continue
        if data.get("apiBase") != address:
            failures += 1
            print(f"FAIL {domain}: на сайте {data.get('apiBase')!r}, а нужно {address!r}")
        elif str(data.get("apiKey") or "") != api_key:
            failures += 1
            print(f"FAIL {domain}: ключ на сайте {('задан' if data.get('apiKey') else 'отсутствует')}, "
                  f"а нужно {('задан' if api_key else 'отсутствует')}")
        elif not quiet:
            key_note = " с ключом" if api_key else ""
            print(f"OK   {domain}: https://{domain}/{RELATIVE_DIR}/{FILE_NAME} -> {address}{key_note}")
    return failures


def ping(address: str) -> bool:
    """401 значит «сервер жив, он закрыт ключом» — этого достаточно."""
    request = urllib.request.Request(address + "/api/health")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status < 500
    except urllib.error.HTTPError as error:
        return error.code < 500
    except (urllib.error.URLError, OSError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Публикация адреса API и ключа панели на сайте")
    parser.add_argument("--address", default="", help="адрес API (по умолчанию из data/tunnel-url.txt)")
    parser.add_argument("--key", default="", help="ключ панели (по умолчанию из GH_API_KEY или data/api-key.txt)")
    parser.add_argument("--no-key", action="store_true", help="опубликовать только адрес")
    parser.add_argument("--domains", nargs="*", default=list(DEFAULT_DOMAINS))
    parser.add_argument("--host", default=os.environ.get("GH_HOST_NAME", "server47.hosting.reg.ru"))
    parser.add_argument("--user", default=os.environ.get("GH_HOST_USER", "u3680668"))
    parser.add_argument("--remote-base", default=os.environ.get("GH_HOST_ROOT", "/var/www/u3680668/data/www"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="молчать, если публиковать нечего")
    parser.add_argument("--skip-ping", action="store_true", help="не проверять адрес перед публикацией")
    args = parser.parse_args(argv)

    address = read_address(args.address)
    if not address:
        if not args.quiet:
            print(f"Адрес не задан и файл {URL_FILE} пуст — публиковать нечего")
        return 0 if args.quiet else 1
    if not address.startswith(("http://", "https://")):
        print(f"Адрес должен начинаться с http:// или https://, а не {address!r}")
        return 1

    api_key = read_api_key(args.key, not args.no_key)
    content = build_document(address, api_key)
    if args.dry_run:
        print(content.decode("utf-8"), end="")
        print(f"--- было бы записано в {RELATIVE_DIR}/{FILE_NAME} на: {', '.join(args.domains)}")
        return 0

    if not args.skip_ping and not ping(address):
        print(f"Адрес {address} не отвечает — публикация отменена")
        return 1

    password = read_password()
    if not password:
        # Из скрипта туннеля это не ошибка: просто нет доступа к хостингу.
        print("Пароль хостинга не задан (GH_HOST_PASSWORD или data/host-password.txt) — адрес не опубликован")
        return 0 if args.quiet else 1

    label = datetime.now().strftime("%H:%M:%S")
    if not args.quiet:
        print(f"Публикую {address}{' с ключом панели' if api_key else ''} "
              f"в {RELATIVE_DIR}/{FILE_NAME} на {', '.join(args.domains)}")
        if not api_key:
            print("Ключ панели не публикуется: нет GH_API_KEY и файла data/api-key.txt")
    failures = upload(args.host, args.user, password, args.remote_base, args.domains, content, args.quiet)
    failures += verify(args.domains, address, api_key, args.quiet)
    if failures:
        print(f"[{label}] не удалось опубликовать адрес ({failures} ошибок)")
        return 1
    print(f"[{label}] адрес API на сайте: {address}{' (ключ панели в файле)' if api_key else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
