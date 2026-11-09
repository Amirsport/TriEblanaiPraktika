# -*- coding: utf-8 -*-
"""Импорт готовых MP3-фрагментов из manifest.json в audio_clips."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/opt/greenhouse")

from backend.db import AUDIO_IN_DB, open_database  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--dir", required=True)
parser.add_argument("--dsn", default="")
args = parser.parse_args()
dsn = args.dsn
if not dsn:
    env = Path("/etc/greenhouse.env").read_text(encoding="utf-8")
    match = re.search(r"^GREENHOUSE_DSN=(.+)$", env, re.M)
    dsn = match.group(1).strip().strip('"').strip("'") if match else ""
db = open_database(None, dsn)
folder = Path(args.dir)
manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
tracks = {str(item["track_key"]): item for item in db.songless_tracks()}
saved = 0
for index, item in enumerate(manifest, start=1):
    key = str(item["track_key"])
    track = tracks.get(key)
    if not track:
        print(f"{index}/{len(manifest)} нет трека {key}", flush=True)
        continue
    data = (folder / item["file"]).read_bytes()
    db.audio_clip_save("songless", key, data, "audio/mpeg",
                       int(item.get("duration_ms") or 8000),
                       str(item.get("source") or "v.animethemes.moe"))
    db.songless_set_audio(str(track["anime"]), AUDIO_IN_DB, clip_start=0,
                          clip_length=float(item.get("duration_ms") or 8000) / 1000,
                          track_key=key)
    saved += 1
    if index % 25 == 0:
        print(f"{index}/{len(manifest)}", flush=True)
print("saved", saved)