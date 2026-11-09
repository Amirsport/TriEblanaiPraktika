# -*- coding: utf-8 -*-
"""Проверка AnimeThemes и Kitsu с выводом по строке."""
import socket
import urllib.request

try:
    import socks
except ImportError:
    socks = None


def get(url: str, proxy: bool = False) -> str:
    if proxy and socks is not None:
        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 10808, rdns=True)
        socket.socket = socks.socksocket
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(100)
            return f"{response.status} {body[:60]!r}"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"


with open("_probe2.txt", "w", encoding="utf-8") as out:
    out.write("animethemes " + get(
        "https://api.animethemes.moe/anime?page%5Bsize%5D=1") + "\n")
    out.flush()
    out.write("kitsu " + get(
        "https://kitsu.io/api/edge/anime?sort=-userCount&page%5Blimit%5D=1") + "\n")
    out.flush()