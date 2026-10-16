# Записи песен

Сюда владелец сайта кладёт аудиофайлы, которые слушает игра «Угадай песню за
10 секунд». Скрипт [`backend/seed_songguess.py`](../../../../backend/seed_songguess.py)
копирует их сюда и прописывает путь в колонку `audio` таблицы `songguess_tracks`:

```powershell
# файлы из своей папки: имена сшиваются с названиями песен
py backend/seed_songguess.py --dsn "postgresql://greenhouse@localhost:5432/greenhouse" `
    --audio C:\music

# если разложить по темам: --category hiphop (или anime, rusrap)
py backend/seed_songguess.py --dsn "..." --audio C:\music\hiphop --category hiphop

# неоднозначные имена — файлом соответствий (ключ можно писать с расширением или без)
py backend/seed_songguess.py --dsn "..." --audio C:\music --map music.json
```

Подходят и «Lose Yourself.mp3», и «Eminem - Lose Yourself.mp3», и «Секс без
перерыва.mp3» — регистр и расширение не важны. Можно не копировать файлы,
а указать ссылку на запись:

```powershell
py backend/seed_songguess.py --dsn "..." --url "hiphop-lose-yourself=https://example.org/lose.mp3"
py backend/seed_songguess.py --dsn "..." --start "hiphop-lose-yourself=42" --length 8
py backend/seed_songguess.py --dsn "..." --clear-audio "hiphop-lose-yourself"
```

`--start` задаёт, с какого места звучит фрагмент (удобно ставить на припев),
`--length` — сколько секунд он длится; игра слушает не больше пяти секунд, даже
если в базе стоит больше.

Посмотреть, что уже привязано, можно так:

```powershell
py backend/seed_songguess.py --dsn "..." --list
```

**Важно про авторские права.** Используйте только те записи, на которые у вас
есть право: свои файлы, материалы с разрешения правообладателя или записи
со свободной лицензией. Песни защищены авторским правом, и выкладывать их на
сайте без разрешения нельзя. В репозитории записей нет — только справочные
сведения о песнях (название, исполнитель, год).

Пустая папка — нормальное состояние: пока в теме меньше четырёх песен
с записью, страница игры честно говорит, что играть нечего.
