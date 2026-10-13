# HTTPS-туннель к домашнему серверу теплицы через SSH (localhost.run).
#
# Зачем: Cloudflare-туннель (см. _tunnel_retry.ps1) в этой сети провайдер глушит —
# канал регистрируется, но данные не проходят (снаружи 530). Обратный SSH-туннель
# этим не страдает: соединение по 22-му порту идёт стабильно.
#
# Требования: системный VPN/TUN-режим (без него сервер туннеля недоступен),
# поднятый домашний сервер и OpenSSH (ssh.exe входит в Windows).
#
# Важно: ssh запускается без ключа -N — localhost.run выдаёт адрес туннеля
# в сессионном канале, а с -N сессия не создаётся и адрес не приходит.
#
# Два режима подключения (см. https://localhost.run/docs/forever-free/):
#   с ключом (по умолчанию): -RemoteUserHost 'localhost.run'
#       адрес сохраняется между переподключениями, но ключ нужно один раз
#       добавить в аккаунт на https://admin.localhost.run/ — иначе адрес не выдаётся;
#   анонимный: -RemoteUserHost 'nokey@localhost.run'
#       работает без аккаунта, но адрес меняется при каждом переподключении.
# Ключ берётся из ~/.ssh (например id_rsa) и ssh-agent, пароль не требуется.
#
# Запуск:
#   powershell -ExecutionPolicy Bypass -File _tunnel_ssh.ps1
#   powershell -ExecutionPolicy Bypass -File _tunnel_ssh.ps1 -Port 8000 -MaxHours 12
#   powershell -ExecutionPolicy Bypass -File _tunnel_ssh.ps1 -RemoteUserHost nokey@localhost.run
#
# Адрес туннеля печатается и сохраняется в data/tunnel-url.txt.
# Остановить: закрыть окно или завершить процессы ssh, запущенные этим скриптом.
param(
    [int]$Port = 8000,
    [int]$MaxHours = 6,
    [string]$RemoteUserHost = 'localhost.run',
    [string]$SshPath = "$env:SystemRoot\System32\OpenSSH\ssh.exe",
    [string]$UrlPattern = 'https://[a-z0-9-]+\.lhr\.(?:life|rocks)'
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$urlFile = Join-Path $root 'data\tunnel-url.txt'
$logFile = Join-Path $env:TEMP 'ssh-tunnel.log'
$attemptLog = Join-Path $env:TEMP 'tunnel-ssh-attempts.log'
$deadline = (Get-Date).AddHours($MaxHours)

if (-not (Test-Path $SshPath)) {
    Write-Host "ssh.exe не найден: $SshPath"
    exit 1
}

function Write-Attempt([string]$message) {
    $line = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Write-Host $line
    Add-Content -Path $attemptLog -Value $line -Encoding UTF8
}

function Get-TunnelUrl([string]$logFile) {
    if (-not (Test-Path $logFile)) { return $null }
    $match = Select-String -Path $logFile -Pattern $UrlPattern -AllMatches | Select-Object -First 1
    if ($match) { return $match.Matches[0].Value.Trim() }
    return $null
}

# Проверяем не журнал, а реальный ответ: 200 с ключом или 401 без него значат,
# что запрос дошёл до сервера теплицы.
function Test-TunnelServes([string]$tunnelUrl) {
    if (-not $tunnelUrl) { return $false }
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (-not (Test-Path $curl)) { return $true }
    $code = & $curl -skS -m 15 -o NUL -w '%{http_code}' "$tunnelUrl/api/health" 2>$null
    return ($code -eq '200' -or $code -eq '401')
}

Write-Attempt "старт: порт $Port, предел $MaxHours ч, журнал $attemptLog"

while ((Get-Date) -lt $deadline) {
    Remove-Item $logFile -ErrorAction SilentlyContinue

    $ssh = Start-Process -FilePath $SshPath `
        -ArgumentList '-o', 'StrictHostKeyChecking=no', '-o', 'ServerAliveInterval=20',
                      '-o', 'ExitOnForwardFailure=yes', '-R', "80:localhost:$Port", $RemoteUserHost `
        -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.err" -PassThru
    Write-Attempt "попытка: ssh PID $($ssh.Id)"

    $url = $null
    for ($i = 0; $i -lt 45; $i++) {
        Start-Sleep -Milliseconds 1000
        $url = Get-TunnelUrl $logFile
        if (-not $url) { $url = Get-TunnelUrl "$logFile.err" }
        if ($url) { break }
        if (-not (Get-Process -Id $ssh.Id -ErrorAction SilentlyContinue)) { break }
    }

    if ($url -and (Test-TunnelServes $url)) {
        $url | Set-Content -Path $urlFile -Encoding ascii
        Write-Attempt "ТУННЕЛЬ РАБОТАЕТ: $url"
        Write-Attempt "адрес сохранён в $urlFile"
        Write-Attempt 'введите его и API-ключ в панели: раздел Режим -> Подключение к серверу'

        $probe = 0
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 20
            if (-not (Get-Process -Id $ssh.Id -ErrorAction SilentlyContinue)) {
                Write-Attempt 'ssh завершился, переподключаюсь'
                break
            }
            $probe++
            if ($probe % 2 -eq 0 -and -not (Test-TunnelServes $url)) {
                Write-Attempt 'ответы через туннель перестали проходить, переподключаюсь'
                break
            }
        }
    } else {
        Write-Attempt 'адрес не получен или туннель не отвечает'
        if ($RemoteUserHost -notmatch 'nokey') {
            Write-Attempt 'если ключ ещё не добавлен в https://admin.localhost.run/, повторите с -RemoteUserHost nokey@localhost.run'
        }
    }

    Stop-Process -Id $ssh.Id -Force -ErrorAction SilentlyContinue
    if ((Get-Date) -lt $deadline) { Start-Sleep -Seconds 20 }
}

Get-Process -Name ssh -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $SshPath } |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Write-Attempt 'время работы истекло, скрипт остановлен'
