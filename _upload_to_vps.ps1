# Выгрузка проекта на VPS и установка сервера «Умной AI-Теплицы» одной командой.
#
# Что делает:
#   1) собирает архив проекта (без .git, .venv, базы и прочего лишнего);
#   2) копирует его на сервер по scp и распаковывает в /opt/greenhouse;
#   3) запускает там _setup_vps.sh: PostgreSQL, служба сервера, nginx, сертификат;
#   4) переносит данные: по ключу -Sqlite — из базы SQLite, по ключу -PgDump —
#      дампом PostgreSQL. Живая база проекта уже PostgreSQL (аккаунты, журналы
#      матчей, персонажи с портретами), поэтому для неё нужен -PgDump.
#
# Примеры:
#   powershell -ExecutionPolicy Bypass -File _upload_to_vps.ps1 -Server 203.0.113.10 `
#       -Domain ai-parnik.ru -Email me@example.com -Sqlite data\greenhouse.sqlite3
#
#   # живая база PostgreSQL: дамп снимается на этой машине и восстанавливается на сервере
#   powershell -ExecutionPolicy Bypass -File _upload_to_vps.ps1 -Server 203.0.113.10 `
#       -Domain ai-parnik.ru -Email me@example.com -PgDump -Dsn "postgresql://greenhouse:пароль@localhost:5432/greenhouse"
#
#   # несколько доменов на одном сервере (панель и отдельный api.)
#   ... -Domain ai-parnik.ru,api.ai-parnik.ru -Email me@example.com
#
#   # панель теплицы и витрина мини-игр двумя доменами на одном сервере
#   powershell -ExecutionPolicy Bypass -File _upload_to_vps.ps1 -Server 203.0.113.10 `
#       -Domain ai-parnik.ru -GamesDomain amrgames.ru -Email me@example.com -PgDump
#
#   # только посмотреть, что будет сделано (архив собирается, загрузки нет)
#   powershell -ExecutionPolicy Bypass -File _upload_to_vps.ps1 -Server 203.0.113.10 -DryRun
#
#   # если на сервере настроен вход по ключу (рекомендуется)
#   ... -Key $env:USERPROFILE\.ssh\id_ed25519
#
# Без -Key ssh спросит пароль в консоли: запускайте скрипт в обычном окне
# PowerShell, а не из автоматизации.
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$User = 'root',
    [string]$Key = '',
    [int]$Port = 22,
    [string[]]$Domain = @(),
    [string[]]$GamesDomain = @(),
    [string]$Email = '',
    [string]$Sqlite = '',
    [switch]$PgDump,
    [string]$Dsn = '',
    [string]$PgDumpPath = '',
    [string]$RemoteRoot = '/opt/greenhouse',
    [switch]$SkipApt,
    [switch]$NoNginx,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$archive = Join-Path $env:TEMP "greenhouse-$stamp.tar.gz"
$remoteArchive = "/tmp/greenhouse-$stamp.tar.gz"
$dumpFile = Join-Path $env:TEMP "greenhouse-dump-$stamp.sql"
$remoteDump = "/tmp/greenhouse-dump-$stamp.sql"
$target = "$User@$Server"

function Require-Tool([string]$name) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $command) { throw "Не найдена программа $name" }
    return $command.Source
}

# pg_dump в PATH есть не всегда (у PostgreSQL свой каталог bin), поэтому ищем и там.
function Find-PgDump([string]$explicit) {
    if ($explicit) {
        if (-not (Test-Path $explicit)) { throw "Не найден pg_dump по пути $explicit" }
        return $explicit
    }
    $command = Get-Command 'pg_dump.exe' -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $found = Get-ChildItem "$env:ProgramFiles\PostgreSQL" -Filter 'pg_dump.exe' -Recurse `
        -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) { return $found.FullName }
    throw 'Не найден pg_dump.exe: укажите -PgDumpPath (например, C:\Program Files\PostgreSQL\17\bin\pg_dump.exe)'
}

$tar = Require-Tool 'tar.exe'
$scp = Require-Tool 'scp.exe'
$ssh = Require-Tool 'ssh.exe'

# ------------------------------------------------------------ 1. архив проекта
$exclude = @(
    '--exclude=.git', '--exclude=.venv', '--exclude=data', '--exclude=__pycache__',
    '--exclude=*.zip', '--exclude=*.pyc', '--exclude=*.sqlite3',
    # адрес прошлого туннеля: на VPS страницы игр берут адрес API у своего домена,
    # а устаревший файл с хостинга отправил бы их на несуществующий адрес
    '--exclude=api-address.json'
)
Write-Output "Собираю архив проекта..."
& $tar $exclude -czf $archive -C $repo .
if (-not (Test-Path $archive)) { throw "Не удалось собрать архив $archive" }
Write-Output ("Архив: {0} ({1:N1} МБ)" -f $archive, ((Get-Item $archive).Length / 1MB))

$sshArgs = @()
if ($Key) { $sshArgs += @('-i', $Key) }
$sshArgs += @('-p', "$Port", '-o', 'StrictHostKeyChecking=accept-new')

# У scp порт задаётся ключом -P (заглавная), а -p означает «сохранить время
# файла»: с общим набором аргументов номер порта уходил как имя файла, и
# загрузка падала с «stat local "22": No such file or directory».
$scpArgs = @()
if ($Key) { $scpArgs += @('-i', $Key) }
$scpArgs += @('-P', "$Port", '-o', 'StrictHostKeyChecking=accept-new')

# При запуске через powershell -File список доменов приходит одной строкой
# («a.ru,b.ru»), поэтому разделяем и его, и повторённые ключи.
$domains = @()
foreach ($item in $Domain) {
    $domains += ($item -split ',' | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() })
}
$gamesDomains = @()
foreach ($item in $GamesDomain) {
    $gamesDomains += ($item -split ',' | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() })
}

$setupArgs = @("--root $RemoteRoot")
foreach ($name in $domains) { $setupArgs += "--domain $name" }
foreach ($name in $gamesDomains) { $setupArgs += "--games-domain $name" }
if ($Email) { $setupArgs += "--email $Email" }
if ($SkipApt) { $setupArgs += '--skip-apt' }
if ($NoNginx) { $setupArgs += '--no-nginx' }
if ($Sqlite -and -not $PgDump) { $setupArgs += "--db $RemoteRoot/data/greenhouse.sqlite3" }
if ($PgDump) { $setupArgs += "--dump $remoteDump" }

$remoteSetup = "$RemoteRoot/_setup_vps.sh"

# Источник данных проверяем до установки: ошибка в пути к базе или в строке
# подключения должна всплывать сразу, а не после установки пакетов.
$sqlitePath = ''
if ($Sqlite -and -not $PgDump) {
    $sqlitePath = (Resolve-Path $Sqlite).Path
    if (-not (Test-Path $sqlitePath)) { throw "Не найдена база $sqlitePath" }
}
# Дамп снимаем и в -DryRun: так видно, что источник отвечает, и сколько он весит.
if ($PgDump) {
    # Источник: -Dsn, иначе переменная окружения, иначе файл data\dsn.txt
    # (каталог data\ в репозиторий не попадает, поэтому пароль там и лежит).
    $source = $Dsn
    if (-not $source) { $source = $env:GREENHOUSE_DSN }
    if (-not $source) {
        $dsnFile = Join-Path $repo 'data\dsn.txt'
        if (Test-Path $dsnFile) { $source = (Get-Content $dsnFile -Raw).Trim() }
    }
    if (-not $source) {
        throw 'Не указан источник данных: -Dsn, GREENHOUSE_DSN или файл data\dsn.txt'
    }
    $pgDumpExe = Find-PgDump $PgDumpPath
    Write-Output 'Снимаю дамп PostgreSQL...'
    # --clean --if-exists: повторный прогон перезаливает таблицы, а не спотыкается
    # о существующие. Владельцев сохраняем: роль greenhouse создаётся установщиком
    # с тем же именем, поэтому таблицы сразу принадлежат приложению.
    & $pgDumpExe --clean --if-exists --format=plain --file $dumpFile $source
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $dumpFile)) {
        throw 'pg_dump не смог снять дамп: проверьте строку подключения -Dsn'
    }
    Write-Output ("Дамп: {0:N1} МБ ({1})" -f ((Get-Item $dumpFile).Length / 1MB), $source)
}

Write-Output ''
Write-Output 'Будет выполнено на сервере:'
Write-Output ("  1) mkdir -p {0} && tar -xzf {1} -C {0}" -f $RemoteRoot, $remoteArchive)
if ($sqlitePath) {
    Write-Output ("  2) копирование {0} в {1}/data/greenhouse.sqlite3" -f $sqlitePath, $RemoteRoot)
}
if ($PgDump) {
    Write-Output ("  2) копирование дампа в {0}" -f $remoteDump)
}
Write-Output ("  3) bash {0} {1}" -f $remoteSetup, ($setupArgs -join ' '))

if ($DryRun) {
    Write-Output ''
    Write-Output 'Режим -DryRun: на сервер ничего не отправлено.'
    Remove-Item $archive -Force -ErrorAction SilentlyContinue
    Remove-Item $dumpFile -Force -ErrorAction SilentlyContinue
    exit 0
}

# --------------------------------------------------------------- 2. публикация
Write-Output ''
Write-Output 'Копирую архив на сервер...'
& $scp @scpArgs $archive "${target}:$remoteArchive"

# Секреты не передаются аргументами командной строки (они видны в списке процессов):
# установщик создаёт их сам и печатает один раз, а на повторном запуске берёт из файла.
Write-Output 'Готовлю проект на сервере...'
# sed снимает возможные CR: если рабочий файл попал в архив после checkout
# на Windows, bash отказался бы работать с «\r» в конце строк.
& $ssh @sshArgs $target "mkdir -p '$RemoteRoot' && tar -xzf '$remoteArchive' -C '$RemoteRoot' && sed -i 's/\r$//' '$remoteSetup' && chmod +x '$remoteSetup'"

if ($sqlitePath) {
    Write-Output 'Копирую базу SQLite для переноса...'
    & $ssh @sshArgs $target "mkdir -p '$RemoteRoot/data'"
    & $scp @scpArgs $sqlitePath "${target}:$RemoteRoot/data/greenhouse.sqlite3"
}

if ($PgDump) {
    Write-Output 'Копирую дамп базы...'
    & $ssh @sshArgs $target "rm -f '$remoteDump'"
    & $scp @scpArgs $dumpFile "${target}:$remoteDump"
}

# ------------------------------------------------------------------ 3. установка
Write-Output 'Запускаю установку на сервере (это займёт несколько минут)...'
Write-Output ''
& $ssh @sshArgs $target "bash '$remoteSetup' $($setupArgs -join ' ')"
$code = $LASTEXITCODE

Write-Output ''
& $ssh @sshArgs $target "rm -f '$remoteArchive' '$remoteDump'"
Remove-Item $archive -Force -ErrorAction SilentlyContinue
Remove-Item $dumpFile -Force -ErrorAction SilentlyContinue

if ($code -ne 0) {
    Write-Output "Установка завершилась с кодом $code."
    Write-Output "Посмотрите журнал на сервере: ssh $target 'journalctl -u greenhouse -n 50 --no-pager'"
    exit $code
}

Write-Output 'Установка завершена. Дальше:'
Write-Output '  * проверьте панель по своему домену;'
Write-Output '  * запустите дома агента: python backend/device_agent.py --server https://<домен> --device-token <токен> --serial COM3;'
Write-Output '  * токены и пароль напечатал установщик (и сохранил в /etc/greenhouse.env на сервере).'
Write-Output ''
Write-Output 'Если панель остаётся на reg.ru, один раз опубликуйте адрес сервера:'
Write-Output '  $env:GH_HOST_PASSWORD = ''пароль хостинга''; python _publish_address.py --address https://<домен>'
