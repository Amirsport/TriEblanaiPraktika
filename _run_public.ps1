# Запуск теплицы для публикации: локальный сервер + HTTPS-туннель Cloudflare.
# Ключ и пароль БД скрипт не хранит — берёт из переменных окружения.
#
# Пример:
#   $env:GREENHOUSE_TOKEN = "длинный-секрет"
#   $env:GREENHOUSE_DSN   = "postgresql://greenhouse@localhost:5432/greenhouse"
#   powershell -ExecutionPolicy Bypass -File _run_public.ps1
#
# Остановить: Stop-Process -Id <PID сервера>, <PID туннеля>
param(
    [int]$Port = 8000,
    [string]$Token = $env:GREENHOUSE_TOKEN,
    [string]$Dsn = $env:GREENHOUSE_DSN,
    [string]$PythonPath = '',
    [string]$CloudflaredPath = 'C:\Program Files (x86)\cloudflared\cloudflared.exe',
    [switch]$NoTunnel
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $Token) {
    Write-Warning 'API-ключ не задан: команды теплице сможет отдать любой, кто узнает адрес. Задайте $env:GREENHOUSE_TOKEN.'
}

if (-not $PythonPath) {
    $venv = Join-Path $root '.venv\Scripts\python.exe'
    if (Test-Path $venv) { $PythonPath = $venv } else { $PythonPath = 'python' }
}

$serverArgs = @('backend/server.py', '--port', $Port, '--host', '127.0.0.1')
if ($Dsn) { $serverArgs += @('--dsn', $Dsn) }
if ($Token) { $serverArgs += @('--token', $Token) }

Write-Host "Сервер: $PythonPath $($serverArgs -join ' ')" -ForegroundColor Cyan
$server = Start-Process -FilePath $PythonPath -ArgumentList $serverArgs -WorkingDirectory $root -PassThru
Write-Host ("PID сервера: {0}" -f $server.Id)

if ($NoTunnel) {
    Write-Host "Туннель не запрошен (-NoTunnel). Локально: http://127.0.0.1:$Port/"
    exit 0
}

if (-not (Test-Path $CloudflaredPath)) {
    Write-Warning "cloudflared не найден: $CloudflaredPath. Установите: winget install Cloudflare.cloudflared"
    Write-Host "Локально сервер уже работает: http://127.0.0.1:$Port/"
    exit 1
}

$log = Join-Path $env:TEMP 'cloudflared-greenhouse.log'
Remove-Item $log -ErrorAction SilentlyContinue
$tunnelArgs = @('tunnel', '--url', "http://127.0.0.1:$Port", '--protocol', 'http2',
                '--no-autoupdate', '--logfile', $log)
$tunnel = Start-Process -FilePath $CloudflaredPath -ArgumentList $tunnelArgs -PassThru
Write-Host ("PID туннеля: {0}" -f $tunnel.Id)

$url = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Path $log) {
        $found = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches |
            Select-Object -First 1
        if ($found) { $url = $found.Matches[0].Value; break }
    }
}

if (-not $url) {
    Write-Warning "Не удалось получить адрес туннеля. Смотрите журнал: $log"
    exit 1
}

$dataDir = Join-Path $root 'data'
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
$url | Set-Content -Path (Join-Path $dataDir 'tunnel-url.txt') -Encoding ascii

Write-Host ''
Write-Host '=== Готово ===' -ForegroundColor Green
Write-Host "Адрес API  : $url" -ForegroundColor Yellow
Write-Host 'Ключ       : тот, что в GREENHOUSE_TOKEN (в консоль не печатается)'
Write-Host "Панель     : http://ai-parnik.ru/  -> раздел «Режим» -> «Подключение к серверу»"
Write-Host 'Вставьте адрес API и ключ, нажмите «Подключиться».'
Write-Host ("Адрес сохранён в: {0}" -f (Join-Path $dataDir 'tunnel-url.txt'))
Write-Host ''
Write-Host 'Остановить всё:'
Write-Host ("  Stop-Process -Id {0},{1}" -f $server.Id, $tunnel.Id)
