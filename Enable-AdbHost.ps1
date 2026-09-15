param(
    [string]$AdbPath = "C:\platform-tools\adb.exe",
    [int]$Port = 5037
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $AdbPath)) {
    throw "ADB not found: $AdbPath"
}

$addresses = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.AddressState -eq "Preferred"
    } |
    Select-Object -ExpandProperty IPAddress

Write-Host "Windows IPv4 candidates: $($addresses -join ', ')"
Write-Host "Starting ADB Server on 0.0.0.0:$Port"
Write-Warning "Only allow trusted/private networks to access TCP $Port. Press Ctrl+C to stop."

& $AdbPath kill-server
& $AdbPath -a -P $Port nodaemon server
