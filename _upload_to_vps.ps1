# Выгрузка проекта на VPS и установка сервера «Умной AI-Теплицы» одной командой.
#
# Что делает:
#   1) собирает архив проекта (без .git, .venv, базы и прочего лишнего);
#   2) копирует его на сервер по scp и распаковывает в /opt/greenhouse;
#   3) запускает там _setup_vps.sh: PostgreSQL, служба сервера, nginx, сертификат;
#   4) по ключу -Sqlite дополнительно переносит базу SQLite (историю теплицы,
#      аккаунты, игры) в PostgreSQL на сервере.
#
# Примеры:
#   powershell -ExecutionPolicy Bypass -File _upload_to_vps.ps1 -Server 203.0.113.10 `
#       -Domain ai-parnik.ru -Email me@example.com -Sqlite data\greenhouse.sqlite3
#
#   # несколько доменов на одном сервере (панель и отдельный api.)
#   ... -Domain ai-parnik.ru,api.ai-parnik.ru -Email me@example.com
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
    [string]$Email = '',
    [string]$Sqlite = '',
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
$target = "$User@$Server"

function Require-Tool([string]$name) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $command) { throw "Не найдена программа $name" }
    return $command.Source
}

$tar = Require-Tool 'tar.exe'
$scp = Require-Tool 'scp.exe'
$ssh = Require-Tool 'ssh.exe'

# ------------------------------------------------------------ 1. архив проекта
$exclude = @(
    '--exclude=.git', '--exclude=.venv', '--exclude=data', '--exclude=__pycache__',
    '--exclude=*.zip', '--exclude=*.pyc', '--exclude=*.sqlite3'
)
Write-Output "Собираю архив проекта..."
& $tar $exclude -czf $archive -C $repo .
if (-not (Test-Path $archive)) { throw "Не удалось собрать архив $archive" }
Write-Output ("Архив: {0} ({1:N1} МБ)" -f $archive, ((Get-Item $archive).Length / 1MB))

$sshArgs = @()
if ($Key) { $sshArgs += @('-i', $Key) }
$sshArgs += @('-p', "$Port", '-o', 'StrictHostKeyChecking=accept-new')

# При запуске через powershell -File список доменов приходит одной строкой
# («a.ru,b.ru»), поэтому разделяем и его, и повторённые ключи.
$domains = @()
foreach ($item in $Domain) {
    $domains += ($item -split ',' | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() })
}

$setupArgs = @("--root $RemoteRoot")
foreach ($name in $domains) { $setupArgs += "--domain $name" }
if ($Email) { $setupArgs += "--email $Email" }
if ($SkipApt) { $setupArgs += '--skip-apt' }
if ($NoNginx) { $setupArgs += '--no-nginx' }
if ($Sqlite) { $setupArgs += "--db $RemoteRoot/data/greenhouse.sqlite3" }

$remoteSetup = "$RemoteRoot/_setup_vps.sh"

Write-Output ''
Write-Output 'Будет выполнено на сервере:'
Write-Output ("  1) mkdir -p {0} && tar -xzf {1} -C {0}" -f $RemoteRoot, $remoteArchive)
if ($Sqlite) {
    Write-Output ("  2) копирование {0} в {1}/data/greenhouse.sqlite3" -f $Sqlite, $RemoteRoot)
}
Write-Output ("  3) bash {0} {1}" -f $remoteSetup, ($setupArgs -join ' '))

if ($DryRun) {
    Write-Output ''
    Write-Output 'Режим -DryRun: на сервер ничего не отправлено.'
    Remove-Item $archive -Force
    exit 0
}

# --------------------------------------------------------------- 2. публикация
Write-Output ''
Write-Output 'Копирую архив на сервер...'
& $scp @sshArgs $archive "${target}:$remoteArchive"

# Секреты не передаются аргументами командной строки (они видны в списке процессов):
# установщик создаёт их сам и печатает один раз, а на повторном запуске берёт из файла.
Write-Output 'Готовлю проект на сервере...'
# sed снимает возможные CR: если рабочий файл попал в архив после checkout
# на Windows, bash отказался бы работать с «\r» в конце строк.
& $ssh @sshArgs $target "mkdir -p '$RemoteRoot' && tar -xzf '$remoteArchive' -C '$RemoteRoot' && sed -i 's/\r$//' '$remoteSetup' && chmod +x '$remoteSetup'"

if ($Sqlite) {
    $dbPath = (Resolve-Path $Sqlite).Path
    if (-not (Test-Path $dbPath)) { throw "Не найдена база $dbPath" }
    Write-Output 'Копирую базу SQLite для переноса...'
    & $ssh @sshArgs $target "mkdir -p '$RemoteRoot/data'"
    & $scp @sshArgs $dbPath "${target}:$RemoteRoot/data/greenhouse.sqlite3"
}

# ------------------------------------------------------------------ 3. установка
Write-Output 'Запускаю установку на сервере (это займёт несколько минут)...'
Write-Output ''
& $ssh @sshArgs $target "bash '$remoteSetup' $($setupArgs -join ' ')"
$code = $LASTEXITCODE

Write-Output ''
& $ssh @sshArgs $target "rm -f '$remoteArchive'"
Remove-Item $archive -Force -ErrorAction SilentlyContinue

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
