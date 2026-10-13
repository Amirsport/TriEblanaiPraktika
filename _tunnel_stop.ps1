# Остановка SSH-туннеля, поднятого _tunnel_ssh.ps1.
#
# Запуск:
#   powershell -ExecutionPolicy Bypass -File _tunnel_stop.ps1
#
# Скрипт читает data/tunnel.pid, завершает процесс скрипта туннеля и запущенный
# им ssh.exe. Если файла нет, он всё равно завершает оставшиеся ssh.exe,
# поднятые из того же пути (System32\OpenSSH) — чтобы туннель точно встал.
param(
    [switch]$KeepUrlFile
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $root 'data\tunnel.pid'
$urlFile = Join-Path $root 'data\tunnel-url.txt'
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

if (-not $KeepUrlFile) { Remove-Item $urlFile -ErrorAction SilentlyContinue }

if ($stopped) {
    Write-Host "туннель остановлен (процессов завершено: $stopped)"
} else {
    Write-Host 'запущенных процессов туннеля не найдено'
}
