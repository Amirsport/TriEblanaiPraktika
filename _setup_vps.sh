#!/usr/bin/env bash
# Установка бэкенда «Умной AI-Теплицы» на VPS: PostgreSQL, служба сервера,
# nginx с сертификатом Let's Encrypt и перенос данных из SQLite.
#
# Запускать на сервере от root, из каталога с проектом (или указав --root):
#
#   bash _setup_vps.sh --domain ai-parnik.ru --email me@example.com
#   bash _setup_vps.sh --domain ai-parnik.ru --domain api.ai-parnik.ru --email me@example.com
#   bash _setup_vps.sh --domain ai-parnik.ru --email me@example.com --db data/greenhouse.sqlite3
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
PORT=8000
DB_NAME="greenhouse"
DB_USER="greenhouse"
EMAIL=""
DB_FILE=""
DOMAINS=()
SKIP_APT=0
NO_NGINX=0
DRY_RUN=0

usage() {
    # Печатаем вводный комментарий из начала файла: он и есть справка.
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
    cat <<'USAGE'
Параметры:
  --domain <имя>     домен сайта; можно несколько раз (например, основной и api.)
  --email <адрес>    почта для Let's Encrypt (без неё сертификат не выпускается)
  --db <файл>        SQLite-база для переноса данных (по умолчанию не переносится)
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
        --email) EMAIL="$2"; shift 2 ;;
        --db) DB_FILE="$2"; shift 2 ;;
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
role_exists="$(run_shell "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\"" || true)"
if [ "$DRY_RUN" = 0 ] && printf '%s' "$role_exists" | grep -q 1; then
    run sudo -u postgres psql -c "ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD'"
else
    run sudo -u postgres psql -c "CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD'"
fi
db_exists="$(run_shell "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\"" || true)"
if [ "$DRY_RUN" = 0 ] && printf '%s' "$db_exists" | grep -q 1; then
    say "   база $DB_NAME уже есть"
else
    run sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER"
fi
run systemctl enable --now postgresql

# ------------------------------------------------------------------- 5. проект
say "== Зависимости проекта =="
if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
    run python3 -m venv "$ROOT_DIR/.venv"
fi
run "$ROOT_DIR/.venv/bin/pip" install --upgrade pip
run "$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"
run chown -R "$SERVICE_USER:$SERVICE_USER" "$ROOT_DIR"

# ------------------------------------------------------------- 6. перенос данных
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
        cat > "$NGINX_SITE" <<NGINXEOF
# Панель, игры и API «Умной AI-Теплицы»: статику и запросы отдаёт наш сервер.
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
}
NGINXEOF
    fi
    say "+ записан $NGINX_SITE (server_name: $server_names)"
    run ln -sfn "$NGINX_SITE" /etc/nginx/sites-enabled/greenhouse
    run nginx -t
    run systemctl reload nginx

    if [ -n "$EMAIL" ]; then
        say "== Сертификат Let's Encrypt =="
        certbot_args=()
        for domain in "${DOMAINS[@]}"; do
            certbot_args+=(-d "$domain")
        done
        run certbot --nginx "${certbot_args[@]}" --email "$EMAIL" --agree-tos \
            --non-interactive --redirect
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
  1. Панель: https://$first_domain/  (она же раздаёт статику и игры с этого сервера)
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
