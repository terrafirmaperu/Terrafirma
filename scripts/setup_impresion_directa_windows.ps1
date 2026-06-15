# Impresión directa Terrafirma — Chrome dedicado con --kiosk-printing
param(
    [string]$Url = 'https://terrafirmaperu.com/pos/frm/ctas/collect/list/',
    [string]$ShortcutName = 'Terrafirma - Impresion directa'
)

$ErrorActionPreference = 'Stop'

$chrome = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $chrome) {
    Write-Host 'Instale Google Chrome para impresión directa.' -ForegroundColor Red
    exit 1
}

$userDataDir = Join-Path $env:LOCALAPPDATA 'TerrafirmaChromeCaja'
New-Item -ItemType Directory -Force -Path $userDataDir | Out-Null

$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop ($ShortcutName + '.lnk')
$batPath = Join-Path $desktop ($ShortcutName + '.bat')

$chromeArgs = @(
    '--kiosk-printing',
    '--disable-print-preview',
    '--disable-popup-blocking',
    "--user-data-dir=`"$userDataDir`"",
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-session-crashed-bubble',
    "--app=`"$Url`""
)

$batContent = @"
@echo off
title Terrafirma - Impresion directa
echo Abriendo Terrafirma con impresion directa...
echo Cierre el Chrome normal antes si la ventana de impresion sigue apareciendo.
start "" "$chrome" $($chromeArgs -join ' ')
"@

Set-Content -Path $batPath -Value $batContent -Encoding ASCII

$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($shortcutPath)
$sc.TargetPath = $chrome
$sc.Arguments = ($chromeArgs -join ' ')
$sc.WorkingDirectory = Split-Path $chrome
$sc.Description = 'Terrafirma caja — imprime sin ventana de Google'
$sc.Save()

Write-Host 'Listo:' -ForegroundColor Green
Write-Host "  $shortcutPath"
Write-Host "  $batPath"
Write-Host ''
Write-Host 'IMPORTANTE:' -ForegroundColor Yellow
Write-Host '  1. Cierre Chrome normal (todas las ventanas).'
Write-Host '  2. Abra Terrafirma SOLO con el acceso directo del escritorio.'
Write-Host '  3. Impresora predeterminada: POS-80-Series para Térmica 80 mm; POS58 Printer(2) para RP Pos 58 mm.'
Write-Host "  4. Perfil Chrome dedicado: $userDataDir"
