# Записи опенингов

Сюда владелец сайта кладёт аудиофайлы, которые слушает игра. Скрипт
[`backend/seed_songless.py`](../../../../backend/seed_songless.py) копирует их
сюда и прописывает путь в колонку `audio` таблицы `songless_tracks`:

```powershell
py backend/seed_songless.py --dsn "postgresql://greenhouse@localhost:5432/greenhouse" `
    --audio C:\music
```

Имя файла сшивается с названием аниме без учёта регистра и расширения
(`наруто.mp3` → «Наруто»). Если имена не совпадают, соответствия задаются
файлом `--map` (JSON вида `{"файл.mp3": "Название аниме"}`).

Можно не копировать файлы, а указать ссылку на запись:

```powershell
py backend/seed_songless.py --dsn "..." --url "Наруто=https://example.org/op.mp3"
py backend/seed_songless.py --dsn "..." --start "Наруто=42" --length 10
py backend/seed_songless.py --dsn "..." --clear-audio "Наруто"
```

`--start` задаёт, с какого места звучит фрагмент (удобно ставить на припев),
`--length` — сколько секунд он длится (по умолчанию 8).

**Можно вообще не копировать файлы в эту папку.** Скрипт
[`songs.py`](../../../../songs.py) берёт треки из базы, нарезает ваши записи и
кладёт MP3 прямо в таблицу `audio_clips`; сервер отдаёт фрагмент из базы, а в
колонке `audio` остаётся маркер `db:clip`:

```powershell
py songs.py --only songless --audio C:\music
py songs.py --only songless --audio C:\music --map music.json --force
```

Записи можно не искать руками: скрипт
[`_fetch_songless_audio.py`](../../../../_fetch_songless_audio.py) ищет опенинги
на YouTube через **YouTube Data API v3**, скачивает звук (`yt-dlp`) и кладёт
фрагменты прямо в базу — тем же `songs.py` и тоже без файлов в этой папке:

```powershell
py _fetch_songless_audio.py --attach --dsn "postgresql://greenhouse@localhost:5432/greenhouse"
```

Ключ API задаётся аргументом `--api-key`, переменной `YOUTUBE_API_KEY` или
файлом `data/youtube-api-key.txt`. Нужен `yt-dlp` (см. `requirements-fetch.txt`) —
он скачивает звук, чтобы `songs.py` нарезал из него 8-секундный фрагмент.

**Важно про авторские права.** Используйте только те записи, на которые у вас
есть право: свои файлы, материалы с разрешением правообладателя или записи
со свободной лицензией. Официальные опенинги защищены авторским правом, и
выкладывать их на сайте нельзя. В репозитории записей нет — только справочные
сведения о треках.

Пустая папка — нормальное состояние: пока в наборе меньше четырёх треков
с записью, страница игры честно говорит, что играть нечего.

Поддерживаются файлы: `.mp3`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.wav`, `.flac`,
`.webm`, `.mp4`.
