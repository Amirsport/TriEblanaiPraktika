# Остановка SSH-туннеля, поднятого _tunnel_ssh.ps1, и сервера теплицы, который
# скрипт туннеля запустил сам (см. data/server.pid).
#
# Запуск:
#   powershell -ExecutionPolicy Bypass -File _tunnel_stop.ps1
#   powershell -ExecutionPolicy Bypass -File _tunnel_stop.ps1 -KeepServer
#
# Скрипт читает data/tunnel.pid, завершает процесс скрипта туннеля и запущенный
# им ssh.exe. Если файла нет, он всё равно завершает оставшиеся ssh.exe,
# поднятые из того же пути (System32\OpenSSH) — чтобы туннель точно встал.
param(
    [switch]$KeepUrlFile,
    [switch]$KeepServer
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root 'data\tunnel.pid'
$urlFile = Join-Path $root 'data\tunnel-url.txt'
$serverPidFile = Join-Path $root 'data\server.pid'
$stopped = 0

if (Test-Path $pidFile) {
    try {
        $info = Get-Content $pidFile -Raw | ConvertFrom-Json
        if ($info.script) {
            $scriptProc = Get-Process -Id $info.script -ErrorAction SilentlyContinue
            if ($scriptProc) {
                Write-Host "останавливаю скрипт туннеля PID $($info.script)"
                Stop-Process -Id $info.script -Force -ErrorAction SilentlyContinue
                $stopped++
            }
        }
    } catch {
        Write-Host "не удалось прочитать $pidFile"
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
} else {
    Write-Host "файл $pidFile не найден — ищу ssh.exe напрямую"
}

$sshPath = "$env:SystemRoot\System32\OpenSSH\ssh.exe"
Get-Process -Name ssh -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $sshPath } |
    ForEach-Object {
        Write-Host "останавливаю ssh PID $($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        $stopped++
    }

# Сервер, поднятый скриптом туннеля, останавливаем вместе с туннелем: иначе на
# сайте остаётся мёртвый адрес, а в системе — забытый процесс. Свой сервер
# (запущенный вручную) не трогаем: в data/server.pid его нет.
if (-not $KeepServer -and (Test-Path $serverPidFile)) {
    try {
        $serverInfo = Get-Content $serverPidFile -Raw | ConvertFrom-Json
        # В файле может быть один номер или список: у python.exe из .venv рядом
        # работает настоящий интерпретатор, и порт держат оба.
        $targets = if ($serverInfo.server -is [array]) { $serverInfo.server } else { @($serverInfo.server) }
        foreach ($serverId in $targets) {
            if (-not $serverId) { continue }
            $serverProc = Get-Process -Id $serverId -ErrorAction SilentlyContinue
            if ($serverProc) {
                Write-Host "останавливаю сервер теплицы PID $serverId"
                Stop-Process -Id $serverId -Force -ErrorAction SilentlyContinue
                $stopped++
            }
        }
    } catch {
        Write-Host "не удалось прочитать $serverPidFile"
    }
    Remove-Item $serverPidFile -ErrorAction SilentlyContinue
}

if (-not $KeepUrlFile) { Remove-Item $urlFile -ErrorAction SilentlyContinue }

if ($stopped) {
    Write-Host "туннель остановлен (процессов завершено: $stopped)"
} else {
    Write-Host 'запущенных процессов туннеля не найдено'
}
