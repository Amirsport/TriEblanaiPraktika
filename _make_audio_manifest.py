# -*- coding: utf-8 -*-
"""Собирает manifest.json по уже готовым MP3 в _audio_db."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
catalog = json.loads((ROOT / "backend" / "songless_catalog.json").read_text(encoding="utf-8"))
folder = ROOT / "_audio_db"
items = []
for track in catalog:
    key = str(track.get("track_key") or track.get("anime") or "")
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    path = folder / f"{digest}.mp3"
    if path.exists() and path.stat().st_size > 5000:
        items.append({
            "track_key": key,
            "file": path.name,
            "duration_ms": int(float(track.get("clip_length") or 8) * 1000),
            "source": "v.animethemes.moe",
        })
(folder / "manifest.json").write_text(
    json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("manifest", len(items))