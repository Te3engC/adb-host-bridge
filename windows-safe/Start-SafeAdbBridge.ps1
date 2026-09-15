#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$AdbPath = "$PSScriptRoot\adb.exe",
    [string]$LinuxHost = "user@<server-ip>",
    [int]$RemotePort = 15038,
    [int]$ReconnectDelaySeconds = 5
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $AdbPath -PathType Leaf)) {
    $parentAdb = Join-Path (Split-Path $PSScriptRoot -Parent) "adb.exe"
    if (Test-Path -LiteralPath $parentAdb -PathType Leaf) {
        $AdbPath = $parentAdb
    }
}
if (-not (Test-Path -LiteralPath $AdbPath -PathType Leaf)) {
    throw "adb.exe not found: $AdbPath. Copy these two files into C:\platform-tools."
}

$ssh = Get-Command ssh.exe -ErrorAction SilentlyContinue
if (-not $ssh) {
    throw "Windows OpenSSH client (ssh.exe) is not installed."
}

$AdbPath = (Resolve-Path -LiteralPath $AdbPath).Path

Write-Host "Starting the local-only Windows ADB server..."
& $AdbPath kill-server | Out-Null
& $AdbPath start-server
if ($LASTEXITCODE -ne 0) {
    throw "Failed to start adb.exe."
}

Write-Host ""
Write-Host "Connected Android devices:"
& $AdbPath devices -l
Write-Host ""
Write-Host "Opening encrypted SSH reverse tunnel:"
Write-Host "  Ubuntu 127.0.0.1:$RemotePort -> Windows 127.0.0.1:5037"
Write-Host "Press Ctrl+C or close this window to stop the bridge."
Write-Host "No Windows firewall rule or scheduled task is created."
Write-Host ""

while ($true) {
    & $ssh.Source `
        -o ExitOnForwardFailure=yes `
        -o ServerAliveInterval=30 `
        -o ServerAliveCountMax=3 `
        -o ConnectTimeout=10 `
        -N `
        -R "127.0.0.1:${RemotePort}:127.0.0.1:5037" `
        $LinuxHost

    $sshExitCode = $LASTEXITCODE
    Write-Warning "SSH tunnel exited with code $sshExitCode; retrying in $ReconnectDelaySeconds seconds."
    Start-Sleep -Seconds $ReconnectDelaySeconds
}
