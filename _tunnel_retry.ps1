# Повторные попытки поднять HTTPS-туннель к домашнему серверу теплицы.
# Нужен, когда провайдер блокирует Cloudflare и туннель не поднимается с первого раза:
# скрипт пробует снова каждые N секунд, а когда получится — держит туннель живым
# и записывает адрес в data/tunnel-url.txt.
#
# Запуск (сервер уже должен быть поднят, например через _run_public.ps1):
#   powershell -ExecutionPolicy Bypass -File _tunnel_retry.ps1
#   powershell -ExecutionPolicy Bypass -File _tunnel_retry.ps1 -MaxHours 24 -IntervalSeconds 300
#
# Остановить: закрыть окно либо Stop-Process -Id <PID cloudflared>.
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

function Stop-StaleTunnel {
    Get-Process -Name cloudflared -ErrorAction SilentlyContinue | ForEach-Object {
        # Останавливаем только зависшие экземпляры, у которых нет соединения
        if ($_.StartTime -lt (Get-Date).AddMinutes(-3)) {
            Write-Attempt "останавливаю зависший cloudflared PID $($_.Id)"
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Attempt "старт: порт $Port, интервал $IntervalSeconds с, предел $MaxHours ч"
Write-Attempt "журнал попыток: $attemptLog"

while ((Get-Date) -lt $deadline) {
    Stop-StaleTunnel
    Remove-Item $LogPath -ErrorAction SilentlyContinue

    $tunnel = Start-Process -FilePath $CloudflaredPath `
        -ArgumentList 'tunnel', '--url', "http://127.0.0.1:$Port", '--protocol', 'http2',
                      '--no-autoupdate', '--logfile', $LogPath -PassThru
    Write-Attempt "попытка: cloudflared PID $($tunnel.Id)"

    $url = $null
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 1000
        $url = Get-TunnelUrl $LogPath
        if ($url) { break }
        if (-not (Get-Process -Id $tunnel.Id -ErrorAction SilentlyContinue)) { break }
    }

    if (-not $url) {
        $reason = 'адрес не получен'
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

    $url | Set-Content -Path $urlFile -Encoding ascii
    Write-Attempt "ТУННЕЛЬ ПОДНЯТ: $url"
    Write-Attempt "адрес сохранён в $urlFile"
    Write-Attempt 'введите его и API-ключ в панели: раздел Режим -> Подключение к серверу'

    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 15
        if (-not (Get-Process -Id $tunnel.Id -ErrorAction SilentlyContinue)) {
            Write-Attempt 'туннель оборвался, пробую снова'
            break
        }
    }
}

Write-Attempt 'время попыток вышло, скрипт остановлен'
