# Crea la app en DigitalOcean App Platform (ejecutar una vez con token en .env.deploy).
# Uso:
#   1. Cree .env.deploy con: DIGITALOCEAN_ACCESS_TOKEN=dop_v1_...
#   2. powershell -ExecutionPolicy Bypass -File deploy/digitalocean/create-app.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $root

$envFile = Join-Path $root '.env.deploy'
if (-not (Test-Path $envFile)) {
    Write-Host 'Falta .env.deploy con DIGITALOCEAN_ACCESS_TOKEN=dop_v1_...' -ForegroundColor Red
    exit 1
}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}
$token = $env:DIGITALOCEAN_ACCESS_TOKEN
if (-not $token) {
    Write-Host 'Defina DIGITALOCEAN_ACCESS_TOKEN en .env.deploy' -ForegroundColor Red
    exit 1
}

$doctl = Get-Command doctl -ErrorAction SilentlyContinue
if (-not $doctl) {
    Write-Host 'Instalando doctl...'
    $zip = Join-Path $env:TEMP 'doctl.zip'
    Invoke-WebRequest -Uri 'https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-windows-amd64.zip' -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $env:TEMP\doctl -Force
    $env:Path = (Join-Path $env:TEMP 'doctl') + ';' + $env:Path
}

& doctl auth init --access-token $token
Write-Host 'Creando app desde .do/app.yaml...'
& doctl apps create --spec (Join-Path $root '.do\app.yaml')
Write-Host 'Listo. En el panel DO complete los SECRET: DJANGO_SECRET_KEY, DATABASE_URL, EMAIL_HOST_PASSWORD, NEO_ADMIN_PASSWORD, DNI_API_TOKEN'
Write-Host 'Al arrancar, migrate + bootstrap crean Seguridad -> Config. API DNI automaticamente.'
Write-Host 'Si la base esta vacia: RUN_INITIAL_SEED=1 python manage.py bootstrap_production --seed --skip-static'
