# Configura impresora POS58 en Windows para tickets Terrafirma.
# Ejecutar en PowerShell:  .\scripts\configure_pos58_windows.ps1

$ErrorActionPreference = 'Continue'
$target = 'POS58 Printer(2)'

Write-Host '=== Impresoras POS detectadas ===' -ForegroundColor Cyan
Get-Printer | Where-Object { $_.Name -like 'POS*' } | Format-Table Name, PrinterStatus, JobCount, PortName, Default -AutoSize

foreach ($old in @('POS58 Printer')) {
    $jobs = Get-PrintJob -PrinterName $old -ErrorAction SilentlyContinue
    if ($jobs) {
        Write-Host "Limpiando cola de: $old" -ForegroundColor Yellow
        $jobs | Remove-PrintJob -ErrorAction SilentlyContinue
    }
}

if (-not (Get-Printer -Name $target -ErrorAction SilentlyContinue)) {
    Write-Host "No se encontro '$target'. Instala el driver POS58 primero." -ForegroundColor Red
    exit 1
}

Write-Host "Estableciendo predeterminada: $target" -ForegroundColor Green
$wmi = Get-WmiObject -Query "SELECT * FROM Win32_Printer WHERE Name='$target'"
if ($wmi) {
    $null = $wmi.SetDefaultPrinter()
}

Write-Host ''
Write-Host 'Abriendo preferencias de impresora...' -ForegroundColor Green
Write-Host 'En el cuadro que se abre:' -ForegroundColor Yellow
Write-Host '  1. Papel: Printer 58 (48mm x 1200mm) o 2 Inch Paper'
Write-Host '  2. Orientacion: Vertical'
Write-Host '  3. Guardar / Aplicar'
Write-Host ''

Start-Process 'rundll32.exe' -ArgumentList ('printui.dll,PrintUIEntry /e /n "' + $target + '"')

Write-Host 'Listo. Prueba imprimir desde Terrafirma con Ctrl+F5 en el navegador.' -ForegroundColor Cyan
