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
# Режимы работы:
#   одиночный (по умолчанию): туннель живёт, пока запущен скрипт; если связь
#       оборвалась, скрипт сообщает об этом и завершается — ничего не перезапускается;
#   с автоподключением: -KeepAlive, скрипт сам переподключается при обрыве
#       (нужно, когда панель должна оставаться на связи долго).
# Окно ssh.exe всегда скрыто, чтобы ничего не всплывало поверх других программ.
#
# Сервер теплицы: скрипт следит и за ним. Перед поднятием туннеля и во время
# работы он проверяет порт и, если сервера нет, поднимает backend/server.py
# (параметры подключения — -Dsn и -Token, переменные GREENHOUSE_DSN и
# GREENHOUSE_TOKEN, а если их нет, файлы data/dsn.txt и data/api-key.txt).
# Без сервера туннель ведёт в пустоту и сайт не открывается. Отключить слежение:
# -NoServer. Свой сервер скрипт не трогает: он поднимает процесс, только когда
# порт молчит.
#
# Запуск:
#   powershell -ExecutionPolicy Bypass -File _tunnel_ssh.ps1
#   powershell -ExecutionPolicy Bypass -File _tunnel_ssh.ps1 -KeepAlive
#   powershell -ExecutionPolicy Bypass -File _tunnel_ssh.ps1 -RemoteUserHost nokey@localhost.run
#
# Адрес туннеля печатается и сохраняется в data/tunnel-url.txt, PID — в data/tunnel.pid.
# Остановить: powershell -ExecutionPolicy Bypass -File _tunnel_stop.ps1
param(
    [int]$Port = 8000,
    [int]$MaxHours = 6,
    [string]$RemoteUserHost = 'localhost.run',
    [string]$SshPath = "$env:SystemRoot\System32\OpenSSH\ssh.exe",
    [string]$UrlPattern = 'https://[a-z0-9-]+\.lhr\.(?:life|rocks)',
    [string]$Dsn = $env:GREENHOUSE_DSN,
    [string]$Token = $env:GREENHOUSE_TOKEN,
    [string]$AdminPassword = $env:GREENHOUSE_ADMIN_PASSWORD,
    [switch]$NoServer,
    [switch]$KeepAlive,
    [switch]$ShowWindow
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$urlFile = Join-Path $root 'data\tunnel-url.txt'
$pidFile = Join-Path $root 'data\tunnel.pid'
$serverPidFile = Join-Path $root 'data\server.pid'
$dsnFile = Join-Path $root 'data\dsn.txt'
$keyFile = Join-Path $root 'data\api-key.txt'
$logFile = Join-Path $env:TEMP 'ssh-tunnel.log'
$attemptLog = Join-Path $env:TEMP 'tunnel-ssh-attempts.log'
$deadline = (Get-Date).AddHours($MaxHours)
$mode = if ($KeepAlive) { 'с автоподключением' } else { 'одиночный' }

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

# Значение из параметра, переменной окружения или файла с секретом в data/.
function Read-Setting([string]$value, [string]$file) {
    if ($value) { return $value }
    if (Test-Path $file) { return (Get-Content $file -Raw).Trim() }
    return ''
}

# Проверяем не журнал, а реальный ответ: 200 с ключом или 401 без него значат,
# что запрос дошёл до сервера теплицы.
function Test-ServerUp([int]$serverPort) {
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (-not (Test-Path $curl)) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $client.Connect('127.0.0.1', $serverPort)
            $client.Close()
            return $true
        } catch {
            return $false
        }
    }
    $code = & $curl -sS -m 10 -o NUL -w '%{http_code}' "http://127.0.0.1:$serverPort/api/health" 2>$null
    return ($code -eq '200' -or $code -eq '401')
}

function Start-GreenhouseServer([int]$serverPort) {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { $python = 'python' }
    $serverArgs = @('backend/server.py', '--host', '127.0.0.1', '--port', $serverPort)
    if ($Dsn) { $serverArgs += @('--dsn', $Dsn) }
    if ($Token) { $serverArgs += @('--token', $Token) }
    if ($AdminPassword) { $serverArgs += @('--admin-password', $AdminPassword) }
    $process = Start-Process -FilePath $python -ArgumentList $serverArgs -WorkingDirectory $root `
        -PassThru -WindowStyle Hidden
    # python.exe из .venv — это трамплин: рядом поднимается настоящий
    # интерпретатор. Запоминаем оба, иначе при остановке останется висеть
    # процесс, который держит порт.
    Start-Sleep -Seconds 2
    $ids = @([int]$process.Id)
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$($process.Id)" -ErrorAction SilentlyContinue |
        ForEach-Object { $ids += [int]$_.ProcessId }
    @{ server = $ids; started = (Get-Date).ToString('s') } |
        ConvertTo-Json -Compress | Set-Content -Path $serverPidFile -Encoding UTF8
    Write-Attempt "сервер теплицы запущен: PID $($ids -join ', ')"
}

# Сервер нужен живому туннелю: без него запросы доходят до 502, а панель
# на сайте просто не открывается. Возвращает $true, когда порт отвечает.
function Ensure-Server([int]$serverPort) {
    if (Test-ServerUp $serverPort) { return $true }
    Start-GreenhouseServer $serverPort
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 1000
        if (Test-ServerUp $serverPort) {
            Write-Attempt "сервер теплицы отвечает: http://127.0.0.1:$serverPort/"
            return $true
        }
    }
    Write-Attempt 'сервер теплицы не поднялся: проверьте базу, ключ и порт'
    return $false
}

# Туннель считается рабочим, только если запрос доходит до сервера теплицы.
function Test-TunnelServes([string]$tunnelUrl) {
    if (-not $tunnelUrl) { return $false }
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (-not (Test-Path $curl)) { return $true }
    $code = & $curl -skS -m 15 -o NUL -w '%{http_code}' "$tunnelUrl/api/health" 2>$null
    return ($code -eq '200' -or $code -eq '401')
}

# Публикация текущего адреса на сайте: поддомен меняется при перезапуске, а
# страницы и панель берут адрес из games/api-address.json (см. _publish_address.py).
# Пароль хостинга берётся из GH_HOST_PASSWORD или из data\host-password.txt;
# без него шаг просто пропускается.
function Publish-Address([string]$Address) {
    $script = Join-Path $root '_publish_address.py'
    if (-not (Test-Path $script)) { return }
    $passwordFile = Join-Path $root 'data\host-password.txt'
    if (-not $env:GH_HOST_PASSWORD -and -not (Test-Path $passwordFile)) {
        Write-Attempt 'адрес не опубликован: нет пароля хостинга (GH_HOST_PASSWORD или data\host-password.txt)'
        return
    }
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { $python = 'python' }
    & $python $script --address $Address --quiet 2>&1 | ForEach-Object { Write-Attempt "публикация: $_" }
}

Write-Attempt "старт: режим $mode, порт $Port, предел $MaxHours ч, журнал $attemptLog"

# Параметры сервера: параметры скрипта, переменные окружения, файлы в data/.
$Dsn = Read-Setting $Dsn $dsnFile
$Token = Read-Setting $Token $keyFile
if ($NoServer) {
    Write-Attempt 'за сервером теплицы не слежу (-NoServer)'
} elseif (Ensure-Server $Port) {
    Write-Attempt 'сервер теплицы на связи'
} else {
    Write-Attempt 'туннель подниму всё равно: сервер можно запустить отдельно'
}

@{ script = $PID; started = (Get-Date).ToString('s'); mode = $mode } |
    ConvertTo-Json -Compress | Set-Content -Path $pidFile -Encoding UTF8

while ((Get-Date) -lt $deadline) {
    Remove-Item $logFile -ErrorAction SilentlyContinue

    $sshArgs = @('-o', 'StrictHostKeyChecking=no', '-o', 'ServerAliveInterval=20',
                 '-o', 'ExitOnForwardFailure=yes', '-R', "80:localhost:$Port", $RemoteUserHost)
    $sshParams = @{
        FilePath = $SshPath
        ArgumentList = $sshArgs
        RedirectStandardOutput = $logFile
        RedirectStandardError = "$logFile.err"
        PassThru = $true
    }
    if (-not $ShowWindow) { $sshParams['WindowStyle'] = 'Hidden' }
    $ssh = Start-Process @sshParams
    Write-Attempt "попытка: ssh PID $($ssh.Id) (окно $(if ($ShowWindow) { 'видимо' } else { 'скрыто' }))"

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
        Publish-Address $url
        Write-Attempt 'дальше адрес подставляется сам; ключ вводится один раз: раздел Режим -> Подключение к серверу'
        if (-not $KeepAlive) {
            Write-Attempt 'одиночный режим: туннель держится, пока запущен этот скрипт'
            Write-Attempt 'остановить: powershell -ExecutionPolicy Bypass -File _tunnel_stop.ps1'
        }

        $probe = 0
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 20
            if (-not (Get-Process -Id $ssh.Id -ErrorAction SilentlyContinue)) {
                if ($KeepAlive) {
                    Write-Attempt 'ssh завершился, переподключаюсь'
                } else {
                    Write-Attempt 'ssh завершился, туннель закрыт (одиночный режим: перезапуска нет)'
                    break
                }
                break
            }
            $probe++
            if ($probe % 2 -eq 0) {
                if (-not $NoServer -and -not (Test-ServerUp $Port)) {
                    Write-Attempt 'сервер теплицы перестал отвечать, поднимаю заново'
                    Ensure-Server $Port | Out-Null
                }
                if (-not (Test-TunnelServes $url)) {
                    if ($KeepAlive) {
                        Write-Attempt 'ответы через туннель перестали проходить, переподключаюсь'
                    } else {
                        Write-Attempt 'ответы через туннель перестали проходить (одиночный режим: перезапуска нет)'
                        break
                    }
                    break
                }
            }
        }
        if (-not $KeepAlive) { break }
    } else {
        Write-Attempt 'адрес не получен или туннель не отвечает'
        if ($RemoteUserHost -notmatch 'nokey') {
            Write-Attempt 'если ключ ещё не добавлен в https://admin.localhost.run/, повторите с -RemoteUserHost nokey@localhost.run'
        }
        if (-not $KeepAlive) {
            Write-Attempt 'одиночный режим: повторной попытки не будет'
            break
        }
    }

    Stop-Process -Id $ssh.Id -Force -ErrorAction SilentlyContinue
    if ((Get-Date) -lt $deadline) { Start-Sleep -Seconds 20 }
}

Get-Process -Name ssh -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $SshPath } |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Remove-Item $pidFile -ErrorAction SilentlyContinue
Write-Attempt 'скрипт остановлен'
