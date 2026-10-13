# Повторные попытки поднять HTTPS-туннель к домашнему серверу теплицы.
# Нужен, когда провайдер режет Cloudflare: скрипт пробует снова каждые N секунд,
# а когда туннель действительно поднимется — держит его живым и обновляет
# data/tunnel-url.txt.
#
# Успехом считается строка «Registered tunnel connection» в журнале cloudflared,
# а не появление адреса: адрес выдаётся раньше, а канал может оборваться сразу
# после регистрации — снаружи это видно кодом 530 при живом процессе.
#
# Запуск (сервер уже должен быть поднят, например через _run_public.ps1):
#   powershell -ExecutionPolicy Bypass -File _tunnel_retry.ps1
#   powershell -ExecutionPolicy Bypass -File _tunnel_retry.ps1 -MaxHours 24 -IntervalSeconds 300
#
# Остановить: закрыть окно либо удалить процесс cloudflared.
param(
    [int]$Port = 8000,
    [int]$IntervalSeconds = 120,
    [int]$MaxHours = 6,
    [string]$CloudflaredPath = 'C:\Program Files (x86)\cloudflared\cloudflared.exe',
    [string]$LogPath = "$env:TEMP\cloudflared-retry.log"
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$urlFile = Join-Path $root 'data\tunnel-url.txt'
$attemptLog = Join-Path $env:TEMP 'tunnel-retry-attempts.log'
$deadline = (Get-Date).AddHours($MaxHours)

if (-not (Test-Path $CloudflaredPath)) {
    Write-Host "cloudflared не найден: $CloudflaredPath"
    Write-Host 'Установите: winget install Cloudflare.cloudflared'
    exit 1
}

function Write-Attempt([string]$message) {
    $line = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Write-Host $line
    Add-Content -Path $attemptLog -Value $line -Encoding UTF8
}

function Get-TunnelUrl([string]$logFile) {
    if (-not (Test-Path $logFile)) { return $null }
    $match = Select-String -Path $logFile -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches |
        Select-Object -First 1
    if ($match) { return $match.Matches[0].Value }
    return $null
}

# Время последнего события заданного вида (ISO-строки сравниваются как текст).
function Get-EventStamp([string]$logFile, [string]$phrase) {
    if (-not (Test-Path $logFile)) { return $null }
    $match = Select-String -Path $logFile -Pattern ('"time":"([^"]+)"[^}]*' + $phrase) | Select-Object -Last 1
    if ($match) { return $match.Matches[0].Groups[1].Value }
    return $null
}

# Туннель считается рабочим, только если соединение зарегистрировано и после него
# не было «Connection terminated».
function Test-TunnelConnected([string]$logFile) {
    $registered = Get-EventStamp $logFile 'Registered tunnel connection'
    if (-not $registered) { return $false }
    $terminated = Get-EventStamp $logFile 'Connection terminated'
    if ($terminated -and $terminated -gt $registered) { return $false }
    return $true
}

function Stop-AllCloudflared {
    Get-Process -Name cloudflared -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Attempt "останавливаю cloudflared PID $($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Attempt "старт: порт $Port, интервал $IntervalSeconds с, предел $MaxHours ч"
Write-Attempt "журнал попыток: $attemptLog"

while ((Get-Date) -lt $deadline) {
    Stop-AllCloudflared
    Remove-Item $LogPath -ErrorAction SilentlyContinue

    $tunnel = Start-Process -FilePath $CloudflaredPath `
        -ArgumentList 'tunnel', '--url', "http://127.0.0.1:$Port", '--protocol', 'http2',
                      '--no-autoupdate', '--logfile', $LogPath -PassThru
    Write-Attempt "попытка: cloudflared PID $($tunnel.Id)"

    $connected = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 1000
        if (Test-TunnelConnected $LogPath) { $connected = $true; break }
        if (-not (Get-Process -Id $tunnel.Id -ErrorAction SilentlyContinue)) { break }
    }

    if (-not $connected) {
        $reason = 'канал не зарегистрирован'
        if (Test-Path $LogPath) {
            $tail = Get-Content $LogPath -ErrorAction SilentlyContinue |
                Where-Object { $_ -match 'error|failed|ERR' } | Select-Object -Last 1
            if ($tail) { $reason = $tail.Trim() }
        }
        Write-Attempt "неудача: $reason"
        Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds $IntervalSeconds
        continue
    }

    $url = Get-TunnelUrl $LogPath
    $url | Set-Content -Path $urlFile -Encoding ascii
    Write-Attempt "ТУННЕЛЬ РАБОТАЕТ: $url"
    Write-Attempt "адрес сохранён в $urlFile"
    Write-Attempt 'введите его и API-ключ в панели: раздел Режим -> Подключение к серверу'

    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 15
        if (-not (Get-Process -Id $tunnel.Id -ErrorAction SilentlyContinue)) {
            Write-Attempt 'процесс туннеля завершился, пробую снова'
            break
        }
        if (-not (Test-TunnelConnected $LogPath)) {
            Write-Attempt 'соединение с Cloudflare оборвалось, пробую снова'
            break
        }
    }
}

Stop-AllCloudflared
Write-Attempt 'время попыток вышло, скрипт остановлен'
