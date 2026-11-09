# -*- coding: utf-8 -*-
"""Выгружает живой набор в backend/songless_catalog.json (для нового запуска)."""
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

with psycopg.connect(os.environ["DSN"], row_factory=dict_row) as conn:
    rows = conn.execute(
        "SELECT track_key, anime, song, artist, year, audio, cover, video, "
        "clip_start, clip_length FROM songless_tracks ORDER BY id").fetchall()
for row in rows:
    audio = str(row.get("audio") or "")
    if audio == "db:clip":
        row["audio"] = str(row.get("video") or "")
    row["clip_start"] = float(row.get("clip_start") or 0)
    row["clip_length"] = float(row.get("clip_length") or 8)
Path("backend/songless_catalog.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("exported", len(rows))