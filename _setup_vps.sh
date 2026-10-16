#!/usr/bin/env bash
# Установка бэкенда «Умной AI-Теплицы» на VPS: PostgreSQL, служба сервера,
# nginx с сертификатом Let's Encrypt и перенос данных из SQLite.
#
# Запускать на сервере от root, из каталога с проектом (или указав --root):
#
#   bash _setup_vps.sh --domain ai-parnik.ru --email me@example.com
#   bash _setup_vps.sh --domain ai-parnik.ru --domain api.ai-parnik.ru --email me@example.com
#   bash _setup_vps.sh --domain ai-parnik.ru --email me@example.com --db data/greenhouse.sqlite3
#   bash _setup_vps.sh --domain ai-parnik.ru --email me@example.com --dump data/greenhouse-dump.sql
#   bash _setup_vps.sh --domain ai-parnik.ru --games-domain amrgames.ru --email me@example.com
#
# --games-domain заводит второй сайт — витрину мини-игр: nginx раздаёт её прямо
# из каталога front/games, поэтому игры открываются по коротким адресам
# (/narutodle/, /csdraft/ и так далее), а не по /games/<игра>/. Запросы /api/
# этого домена уходят серверу теплицы, так что страницы игр не спрашивают адрес
# сервера. Название «Умная AI-Теплица» и запрет индексации в общих страницах игр
# на этом домене подменяются на AmrGames (панель теплицы это не затрагивает).
#
# --dump принимает дамп PostgreSQL (pg_dump --clean --if-exists), снятый с рабочей
# базы: так переносятся аккаунты, журналы матчей, персонажи с портретами и всё
# остальное. Если переданы и --db, и --dump, восстанавливается дамп, а SQLite
# пропускается: иначе одни и те же записи попали бы в базу дважды.
#
# Скрипт можно запускать повторно: секреты и данные не пересоздаются, а служба
# и конфиг nginx просто обновляются. Посмотреть, что будет сделано, без изменений:
#
#   bash _setup_vps.sh --domain ai-parnik.ru --dry-run
#
# Домашний агент запускается отдельно — на компьютере, где воткнута Arduino
# (команду скрипт печатает в конце).
set -euo pipefail

ROOT_DIR="/opt/greenhouse"
SERVICE_USER="greenhouse"
ENV_FILE="/etc/greenhouse.env"
SERVICE_FILE="/etc/systemd/system/greenhouse.service"
NGINX_SITE="/etc/nginx/sites-available/greenhouse"
NGINX_GAMES_SITE="/etc/nginx/sites-available/amrgames"
PORT=8000
DB_NAME="greenhouse"
DB_USER="greenhouse"
EMAIL=""
DB_FILE=""
DUMP_FILE=""
DOMAINS=()
GAMES_DOMAINS=()
SKIP_APT=0
NO_NGINX=0
DRY_RUN=0

usage() {
    # Печатаем вводный комментарий из начала файла: он и есть справка.
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
    cat <<'USAGE'
Параметры:
  --domain <имя>     домен сайта; можно несколько раз (например, основной и api.)
  --games-domain <имя>
                     домен витрины игр: второй сайт со страницами из front/games;
                     можно несколько раз (например, с www.)
  --email <адрес>    почта для Let's Encrypt (без неё сертификат не выпускается)
  --db <файл>        SQLite-база для переноса данных (по умолчанию не переносится)
  --dump <файл>      дамп PostgreSQL (pg_dump --clean --if-exists) для переноса данных
  --root <каталог>   где лежит проект (по умолчанию /opt/greenhouse)
  --port <номер>     локальный порт сервера (по умолчанию 8000)
  --skip-apt         не ставить пакеты (если уже установлены)
  --no-nginx         не настраивать nginx и сертификат
  --dry-run          только показать, что будет сделано
USAGE
}

say() { printf '%s\n' "$*"; }

run() {
    say "+ $*"
    if [ "$DRY_RUN" = 0 ]; then
        "$@"
    fi
}

run_shell() {
    say "+ $*"
    if [ "$DRY_RUN" = 0 ]; then
        bash -c "$*"
    fi
}

capture() {
    # То же, что run_shell, но без печати команды: вывод нужен целиком в
    # переменной. Иначе в неё попадала бы и строка «+ sudo ... SELECT 1 ...»,
    # и проверка «уже существует» срабатывала бы на чистом сервере.
    if [ "$DRY_RUN" = 0 ]; then
        bash -c "$*"
    fi
}

random_hex() {
    python3 -c 'import secrets,sys; print(secrets.token_hex(int(sys.argv[1])))' "$1"
}

env_value() {
    # Значение KEY=... из файла окружения (пусто, если файла или ключа нет).
    [ -f "$ENV_FILE" ] && sed -n "s/^$1=//p" "$ENV_FILE" | head -1 || true
}

while [ $# -gt 0 ]; do
    case "$1" in
        --domain) DOMAINS+=("$2"); shift 2 ;;
        --games-domain) GAMES_DOMAINS+=("$2"); shift 2 ;;
        --email) EMAIL="$2"; shift 2 ;;
        --db) DB_FILE="$2"; shift 2 ;;
        --dump) DUMP_FILE="$2"; shift 2 ;;
        --root) ROOT_DIR="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --skip-apt) SKIP_APT=1; shift ;;
        --no-nginx) NO_NGINX=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) say "Неизвестный параметр: $1"; usage; exit 2 ;;
    esac
done

if [ "$(id -u)" != "0" ] && [ "$DRY_RUN" = 0 ]; then
    say "Запускать нужно от root: sudo bash $0 --domain ... --email ..."
    exit 1
fi
if [ ! -f "$ROOT_DIR/backend/server.py" ]; then
    say "В $ROOT_DIR нет backend/server.py — скопируйте туда проект (или укажите --root)."
    exit 1
fi
if [ "$NO_NGINX" = 0 ] && [ ${#DOMAINS[@]} -eq 0 ]; then
    say "Укажите домен: --domain ai-parnik.ru (или --no-nginx, чтобы настроить позже)."
    exit 2
fi
if [ ${#GAMES_DOMAINS[@]} -gt 0 ] && [ "$NO_NGINX" = 1 ]; then
    say "--games-domain настраивает только nginx: без nginx домен витрины пропущен"
    GAMES_DOMAINS=()
fi
if [ ${#GAMES_DOMAINS[@]} -gt 0 ] && [ ! -f "$ROOT_DIR/front/games/index.html" ]; then
    say "В $ROOT_DIR нет front/games/index.html — витрину игр раздавать не из чего."
    exit 3
fi

# ---------------------------------------------------------------- 1. пакеты
if [ "$SKIP_APT" = 0 ]; then
    say "== Пакеты =="
    run apt-get update
    run apt-get install -y python3 python3-venv python3-pip postgresql nginx
    if [ "$NO_NGINX" = 0 ] && [ -n "$EMAIL" ]; then
        run apt-get install -y certbot python3-certbot-nginx
    else
        say "   (certbot не ставим: нет --email или задан --no-nginx)"
    fi
fi

# ------------------------------------------------------------- 2. пользователь
say "== Служба и каталог =="
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    run useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi
run install -d -o "$SERVICE_USER" -g "$SERVICE_USER" "$ROOT_DIR/data"

# ------------------------------------------------------------------ 3. секреты
say "== Секреты =="
DB_PASSWORD="$(env_value DB_PASSWORD)"
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD="$(random_hex 16)"
fi
API_TOKEN="$(env_value GREENHOUSE_TOKEN)"
[ -n "$API_TOKEN" ] || API_TOKEN="$(random_hex 24)"
DEVICE_TOKEN="$(env_value GREENHOUSE_DEVICE_TOKEN)"
[ -n "$DEVICE_TOKEN" ] || DEVICE_TOKEN="$(random_hex 24)"
ADMIN_PASSWORD="$(env_value GREENHOUSE_ADMIN_PASSWORD)"
[ -n "$ADMIN_PASSWORD" ] || ADMIN_PASSWORD="$(random_hex 12)"
DSN="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"

if [ -f "$ENV_FILE" ]; then
    say "   файл $ENV_FILE уже есть — беру пароли из него"
else
    say "   создаю $ENV_FILE (пароли печатаю ниже один раз)"
    if [ "$DRY_RUN" = 0 ]; then
        install -m 600 /dev/null "$ENV_FILE"
        cat > "$ENV_FILE" <<ENVEOF
# Секреты сервера «Умной AI-Теплицы». Читает только systemd (служба greenhouse).
DB_PASSWORD=$DB_PASSWORD
GREENHOUSE_DSN=$DSN
GREENHOUSE_TOKEN=$API_TOKEN
GREENHOUSE_DEVICE_TOKEN=$DEVICE_TOKEN
GREENHOUSE_ADMIN_PASSWORD=$ADMIN_PASSWORD
ENVEOF
        chmod 600 "$ENV_FILE"
    fi
fi

# ---------------------------------------------------------------- 4. PostgreSQL
say "== PostgreSQL =="
role_exists="$(capture "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\"" || true)"
if [ "$DRY_RUN" = 0 ] && printf '%s' "$role_exists" | grep -qx 1; then
    run sudo -u postgres psql -c "ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD'"
else
    run sudo -u postgres psql -c "CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD'"
fi
db_exists="$(capture "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\"" || true)"
if [ "$DRY_RUN" = 0 ] && printf '%s' "$db_exists" | grep -qx 1; then
    say "   база $DB_NAME уже есть"
else
    run sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER"
fi
run systemctl enable --now postgresql

# ------------------------------------------------------------------- 5. проект
say "== Зависимости проекта =="
# Проекту нужен Python 3.11 и новее (см. README): ищем подходящий
# интерпретатор, а на старом останавливаемся с понятным текстом — иначе
# окружение соберётся, но сервер на нём не запустится.
PYTHON_BIN=""
for candidate in python3 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 && \
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PYTHON_BIN="$candidate"
        break
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    say "   нужен Python 3.11 или новее, а в системе $(python3 --version 2>&1)"
    say "   поставьте его отдельно: apt-get install -y python3.12 python3.12-venv"
    exit 3
fi
say "   интерпретатор: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    # Окружение прошлых версий могло собраться на Python 3.9 или 3.10: такие
    # больше не поддерживаются, поэтому просим пересобрать его вручную.
    if ! "$ROOT_DIR/.venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        say "   в $ROOT_DIR/.venv старый Python: $("$ROOT_DIR/.venv/bin/python" --version 2>&1)"
        say "   пересоберите окружение: rm -rf $ROOT_DIR/.venv && $PYTHON_BIN -m venv $ROOT_DIR/.venv"
        exit 3
    fi
else
    run "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
fi
run "$ROOT_DIR/.venv/bin/pip" install --upgrade pip
run "$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"
run chown -R "$SERVICE_USER:$SERVICE_USER" "$ROOT_DIR"

# ------------------------------------------------------------- 6. перенос данных
# Дамп PG важнее SQLite: он снят с рабочей базы, и повторный прогон не должен
# накладывать одни и те же записи дважды.
if [ -n "$DUMP_FILE" ] && [ -n "$DB_FILE" ]; then
    say "== Перенос данных =="
    say "   передан и --dump, и --db: восстанавливаю дамп, SQLite пропускаю"
    DB_FILE=""
fi

if [ -n "$DUMP_FILE" ]; then
    say "== Перенос данных из дампа PostgreSQL =="
    if [ ! -f "$DUMP_FILE" ]; then
        say "   файла $DUMP_FILE нет — перенос пропущен"
    else
        run_shell "sudo -u postgres psql -v ON_ERROR_STOP=1 -q -d '$DB_NAME' -f '$DUMP_FILE'"
        # Дамп снят с рабочей базы тем же пользователем, поэтому владелец таблиц
        # совпадает, а на всякий случай выдаём права схемы приложению.
        run_shell "sudo -u postgres psql -q -d '$DB_NAME' -c \
            \"GRANT ALL ON SCHEMA public TO $DB_USER\""
        run_shell "sudo -u postgres psql -tAc \"SELECT 'users=' || (SELECT count(*) FROM users) \
            || ' characters=' || (SELECT count(*) FROM narutodle_characters)\" -d '$DB_NAME'" || true
    fi
fi

if [ -n "$DB_FILE" ]; then
    say "== Перенос данных из SQLite =="
    if [ ! -f "$DB_FILE" ]; then
        say "   файла $DB_FILE нет — перенос пропущен"
    else
        target="$ROOT_DIR/data/greenhouse.sqlite3"
        if [ "$(readlink -f "$DB_FILE")" != "$(readlink -f "$target" 2>/dev/null || echo "$target")" ]; then
            run cp "$DB_FILE" "$target"
        fi
        run chown "$SERVICE_USER:$SERVICE_USER" "$target"
        run_shell "cd '$ROOT_DIR' && sudo -u $SERVICE_USER GREENHOUSE_DSN='$DSN' \
            .venv/bin/python backend/migrate_to_postgres.py --from data/greenhouse.sqlite3"
    fi
fi

# -------------------------------------------------------------------- 7. служба
say "== Служба сервера =="
if [ "$DRY_RUN" = 0 ]; then
    cat > "$SERVICE_FILE" <<UNITEOF
[Unit]
Description=Умная AI-Теплица: API, база и панель
After=network.target postgresql.service

[Service]
User=$SERVICE_USER
WorkingDirectory=$ROOT_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$ROOT_DIR/.venv/bin/python $ROOT_DIR/backend/server.py --host 127.0.0.1 --port $PORT --device-remote
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNITEOF
fi
say "+ записан $SERVICE_FILE"
run systemctl daemon-reload
run systemctl enable greenhouse
run systemctl restart greenhouse

# --------------------------------------------------------------------- 8. nginx
if [ "$NO_NGINX" = 0 ]; then
    say "== nginx =="
    server_names="${DOMAINS[*]}"
    if [ "$DRY_RUN" = 0 ]; then
        {
            cat <<NGINXEOF
# Панель и API «Умной AI-Теплицы»: статику и запросы отдаёт наш сервер.
server {
    listen 80;
    listen [::]:80;
    server_name $server_names;

    client_max_body_size 8m;   # фрагменты записей для «Аниме-сонглесса»

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
NGINXEOF
            # Мини-игры уехали на витрину (--games-domain): на домене панели их
            # нет, чтобы раздел не жил в двух местах. Записи игр тоже закрыты:
            # их отдаёт витрина через свой /api/. Исключение — файл с адресом
            # API и ключом панели: из него браузеры с устаревшим адресом
            # туннеля узнают новый (см. _publish_address.py).
            if [ ${#GAMES_DOMAINS[@]} -gt 0 ]; then
                cat <<GONEEOF

    location = /games/api-address.json {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location = /games {
        return 404;
    }
    location ^~ /games/ {
        return 404;
    }
GONEEOF
            fi
            printf '}\n'
        } > "$NGINX_SITE"
    fi
    say "+ записан $NGINX_SITE (server_name: $server_names)"
    run ln -sfn "$NGINX_SITE" /etc/nginx/sites-enabled/greenhouse

    # Второй сайт — витрина игр. Игры живут в том же проекте, что и панель,
    # поэтому домен витрины раздаёт каталог front/games как корень сайта, а
    # запросы /api/ переправляет тому же серверу теплицы.
    if [ ${#GAMES_DOMAINS[@]} -gt 0 ]; then
        games_names="${GAMES_DOMAINS[*]}"
        panel_host="${DOMAINS[0]}"
        # sub_filter есть в nginx из штатных пакетов Debian и Ubuntu. Если его
        # вдруг нет, витрина останется с прежним названием, но сайт будет цел.
        branding=0
        if nginx -V 2>&1 | grep -q -- '--with-http_sub_module'; then
            branding=1
        else
            say "   в nginx нет http_sub_module: название витрины не подменяется"
        fi
        if [ "$DRY_RUN" = 0 ]; then
            {
                cat <<GAMESEOF
# Витрина мини-игр AmrGames: страницы и записи лежат на диске, а сами игры
# ходят в /api/ этого же домена — его переправляем серверу теплицы.
server {
    listen 80;
    listen [::]:80;
    server_name $games_names;

    root $ROOT_DIR/front/games;
    index index.html;

    client_max_body_size 8m;   # фрагменты записей для «Аниме-сонглесса»

    # Страницы игр лежат в подкаталогах корня, а общие стили и иконки проекта —
    # на уровень выше: со страниц ссылки ../css и ../icons ведут в корень сайта.
    location ^~ /css/ {
        alias $ROOT_DIR/front/css/;
        add_header Cache-Control "no-cache, must-revalidate";
    }
    location ^~ /icons/ {
        alias $ROOT_DIR/front/icons/;
        expires 30d;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        add_header Cache-Control "no-cache, must-revalidate";
        try_files \$uri \$uri/ \$uri/index.html =404;
    }

    # Файл с адресом панели на витрине не нужен: страницы игр общие с панелью, и
    # с ним они уходили бы на её домен. Пустой адрес значит «тот же домен» — на
    # витрине это её собственный /api/, — а ключ остаётся, чтобы страницы играли
    # без настройки.
    location = /api-address.json {
        default_type application/json;
        return 200 "{\"apiBase\":\"\",\"apiKey\":\"$API_TOKEN\"}";
    }
GAMESEOF
                if [ "$branding" = 1 ]; then
                    # Страницы витрины и игр общие с панелью теплицы, поэтому
                    # название сайта и запрет индексации подменяем здесь, на
                    # домене витрины. Тексты взяты из front/games/index.html:
                    # если их там поправят, поправить нужно и здесь.
                    cat <<BRANDEOF

    # Скрипты тоже фильтруем: у драфтов заголовок вкладки ставит draft.js.
    sub_filter_types text/html text/javascript application/javascript;
    sub_filter_once off;
    sub_filter "<meta name=\"robots\" content=\"noindex, nofollow\">" "<meta name=\"robots\" content=\"index, follow\">";
    sub_filter "· Умная AI-Теплица" "· AmrGames";
    sub_filter "<h1>Игровая комната</h1>" "<h1>AmrGames</h1>";
    sub_filter "<p>Онлайн мини-игры проекта «Умная AI-Теплица»</p>" "<p>Мини-игры проекта AmrGames</p>";
    sub_filter "<a class=\"icon-btn\" href=\"../\" title=\"Вернуться к панели теплицы\">←</a>" "<a class=\"icon-btn\" href=\"https://$panel_host/\" title=\"Панель теплицы\">←</a>";
BRANDEOF
                fi
                printf '}\n'
            } > "$NGINX_GAMES_SITE"
        fi
        say "+ записан $NGINX_GAMES_SITE (server_name: $games_names)"
        run ln -sfn "$NGINX_GAMES_SITE" /etc/nginx/sites-enabled/amrgames
    fi

    run nginx -t
    run systemctl reload nginx

    if [ -n "$EMAIL" ]; then
        say "== Сертификат Let's Encrypt =="
        certbot_args=()
        for domain in "${DOMAINS[@]}" "${GAMES_DOMAINS[@]}"; do
            certbot_args+=(-d "$domain")
        done
        # --expand: повторный запуск с новыми доменами (например, когда
        # добавляется витрина игр) расширяет уже выпущенный сертификат,
        # а не спрашивает подтверждение.
        run certbot --nginx "${certbot_args[@]}" --email "$EMAIL" --agree-tos \
            --non-interactive --redirect --expand
        # Если сертификат уже существовал и перевыпуск не потребовался, certbot
        # мог не трогать nginx, а vhost выше записан заново без TLS: доводим
        # установку сертификата до конфига.
        if [ -f "/etc/letsencrypt/live/${DOMAINS[0]}/fullchain.pem" ] \
            && ! grep -q ssl_certificate "$NGINX_SITE"; then
            run certbot install --nginx --cert-name "${DOMAINS[0]}" --redirect \
                --non-interactive
        fi
    else
        say "   сертификат не выпускаю: не задан --email"
    fi
fi

# ------------------------------------------------------------------- 9. проверка
say "== Проверка =="
if [ "$DRY_RUN" = 0 ]; then
    sleep 3
    if curl -fsS -H "X-Api-Token: $API_TOKEN" "http://127.0.0.1:$PORT/api/health" >/dev/null; then
        say "   сервер отвечает на 127.0.0.1:$PORT"
    else
        say "   сервер не ответил — смотрите журнал: journalctl -u greenhouse -n 50 --no-pager"
    fi
    status="$(systemctl is-active greenhouse || true)"
    say "   служба greenhouse: $status"
fi

first_domain="${DOMAINS[0]:-<домен>}"
cat <<FINALE

Готово. Что дальше:
  1. Панель: https://$first_domain/  (панель, API и статика проекта)
  2. Ключ панели: $API_TOKEN
  3. Токен агента: $DEVICE_TOKEN
  4. Пароль администратора: $ADMIN_PASSWORD (смените после входа, если он был задан здесь)
  5. Агент запускается дома, где воткнута Arduino:
       python backend/device_agent.py --server https://$first_domain --device-token $DEVICE_TOKEN --serial COM3
     без --serial агент работает эмулятором, чтобы проверить связку заранее.
  6. Если панель открывается с другого домена, укажите адрес API в разделе
     «Режим» → https://$first_domain (панель запомнит его в браузере).
  7. Журнал сервера: journalctl -u greenhouse -f
FINALE

if [ ${#GAMES_DOMAINS[@]} -gt 0 ]; then
    games_domain="${GAMES_DOMAINS[0]}"
    cat <<GAMESFINALE

Витрина игр (--games-domain):
  https://$games_domain/          — «Игровая комната» под названием AmrGames
  https://$games_domain/narutodle/ и другие игры — по коротким адресам
  Поисковикам витрина открыта, а /api/ того же домена идёт на сервер теплицы.
GAMESFINALE
fi
