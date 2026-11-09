# -*- coding: utf-8 -*-
"""Готовит колонку track_key: аниме больше не уникально, трек — уникален."""
import os

import psycopg

STATEMENTS = (
    "ALTER TABLE songless_tracks ADD COLUMN IF NOT EXISTS track_key TEXT NOT NULL DEFAULT ''",
    "UPDATE songless_tracks SET track_key = anime WHERE track_key = ''",
    "DROP INDEX IF EXISTS idx_songless_tracks_anime",
    "CREATE INDEX IF NOT EXISTS idx_songless_tracks_anime ON songless_tracks (anime)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_songless_tracks_key ON songless_tracks (track_key)",
)

with psycopg.connect(os.environ["DSN"]) as conn:
    for statement in STATEMENTS:
        conn.execute(statement)
    conn.commit()
print("track_key schema ok")