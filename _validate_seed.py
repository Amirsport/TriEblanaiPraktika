import json
import pathlib
import sys

sys.path.insert(0, ".")
from backend.narutodle_data import CHARACTERS, ARCS, VILLAGE_COLORS, village_color  # noqa: E402

rows = json.loads(pathlib.Path("_csv_rows.json").read_text(encoding="utf-8"))
by_name = {item["name"]: item for item in CHARACTERS}
print("персонажей в narutodle_data.py:", len(CHARACTERS))
print("уникальных имён:", len(by_name))

problems = []
for row in rows:
    item = by_name.get(row["name"])
    if item is None:
        problems.append(f"нет в наборе: {row['name']}")
        continue
    checks = [
        ("gender", item["gender"], row["gender"]),
        ("village", item["village"], row["village"]),
        ("clan", item["clan"], row["clan"]),
        ("nature", list(item["nature"]), row["nature"]),
        ("jinchuriki", item["jinchuriki"], row["jinchuriki"]),
        ("debut", item["debut"], row["debut"]),
        ("color", village_color(item["village"]), row["color"]),
    ]
    for label, got, want in checks:
        want_norm = "Хидан и Какудзу" if want == "Хидан и Какузу" else want
        if got != want_norm:
            problems.append(f"{row['name']}: {label} {got!r} != {want!r}")
    expected_kekkei = "нет" if row["name"] == "Наруто Узумаки" else row["kekkei"]
    if item["kekkei"] != expected_kekkei:
        problems.append(f"{row['name']}: kekkei {item['kekkei']!r} != {expected_kekkei!r}")

extra = [name for name in by_name if name not in {row["name"] for row in rows}]
print("лишних имён в наборе:", extra or "нет")
print("проблем:", len(problems))
for problem in problems[:20]:
    print("  ", problem)

print("\nарки вне ARCS:", sorted({item["debut"] for item in CHARACTERS if item["debut"] not in ARCS}))
print("деревни вне палитры:", sorted({item["village"] for item in CHARACTERS
                                     if item["village"] not in VILLAGE_COLORS}))
print("Наруто:", {key: by_name["Наруто Узумаки"][key] for key in
                  ("village", "clan", "nature", "kekkei", "jinchuriki", "debut")})