# Deploy TerraFirma en DigitalOcean

Guía para **App Platform** (recomendado, con PostgreSQL gestionado) o **Droplet** (VPS + nginx).

## Requisitos previos

- Repositorio Git con la carpeta `app/` como raíz del proyecto Django (`manage.py` en la raíz del repo o usar `source_dir` en App Platform).
- Dominio apuntando al servidor (registro A / CNAME).
- Variables de entorno (ver `deploy/digitalocean/env.example`).

## Opción A — App Platform

1. En [DigitalOcean](https://cloud.digitalocean.com/apps) → **Create App** → conectar GitHub/GitLab.
2. Si el repo incluye la carpeta padre, indique **Source Directory**: `app` (o la ruta donde está `manage.py`).
3. Edite `.do/app.yaml`: `github.repo`, `DJANGO_ALLOWED_HOSTS`, dominio.
4. Cree la base **PostgreSQL** en el mismo app (el spec ya define `databases`).
5. En **Environment Variables**, marque como **SECRET**: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `EMAIL_HOST_PASSWORD`, `DNI_API_TOKEN`, `NEO_ADMIN_PASSWORD`.
6. **Build command** (ya en el yaml o en la UI):

   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
   ```

7. El contenedor ejecuta automáticamente `migrate` y `bootstrap_production` al arrancar (`RUN_MIGRATE` / `RUN_BOOTSTRAP` en `.do/app.yaml`). Eso crea el submódulo **Seguridad → Config. API DNI** y copia `DNI_API_TOKEN` del entorno a la base de datos.

   Si la base está vacía y faltan módulos, puede forzar el seed una vez:

   ```bash
   RUN_INITIAL_SEED=1 python manage.py bootstrap_production --seed --skip-static
   ```

8. Verifique en **Seguridad → Config. API DNI** que el API Key esté guardado y use **Probar API**.

9. En **Settings → Domains**, añada `terrafirmaperu.com` y active HTTPS.

**Nota:** Suba `media/` con contratos/plantillas vía volumen persistente o almacenamiento externo si la app es stateless; en App Platform el disco es efímero salvo que use un volume.

## Opción B — Droplet (Ubuntu)

### 1. Crear Droplet

- Ubuntu 22.04 LTS, mínimo 1 GB RAM (2 GB recomendado por WeasyPrint/docx).
- Añada su SSH key.

### 2. Base de datos

Cree **Managed Database → PostgreSQL** en DigitalOcean y copie la connection string a `DATABASE_URL` en `.env`.

### 3. Subir código

```bash
sudo mkdir -p /var/www/terrafirma
sudo chown $USER:www-data /var/www/terrafirma
git clone <su-repo> /var/www/terrafirma/app
cd /var/www/terrafirma/app
cp deploy/digitalocean/env.example .env
nano .env   # completar SECRET_KEY, DATABASE_URL, etc.
```

### 4. Bootstrap del servidor

```bash
sudo bash deploy/digitalocean/scripts/bootstrap_droplet.sh
source venv/bin/activate
set -a && source .env && set +a
python manage.py bootstrap_production --seed
sudo systemctl enable --now terrafirma
sudo certbot --nginx -d terrafirmaperu.com -d www.terrafirmaperu.com
```

### 5. Actualizaciones

```bash
cd /var/www/terrafirma/app
git pull
bash deploy/digitalocean/scripts/deploy.sh
```

## Comandos útiles

| Comando | Uso |
|---------|-----|
| `python manage.py bootstrap_production` | Migrar + estáticos + módulos + Config. API DNI |
| `python manage.py bootstrap_production --seed` | Incluir datos iniciales |
| `python manage.py ensure_dni_api_module` | Solo menú Seguridad y fila de configuración DNI |
| `python manage.py ensure_neo_superuser --password '...'` | Restablecer admin Neo |
| `python manage.py clear_operational_data --no-input` | Vaciar ventas/clientes de prueba |

## Checklist antes de producción

- [ ] `DJANGO_DEBUG=0` y `DJANGO_SECRET_KEY` único
- [ ] `DJANGO_ALLOWED_HOSTS` con dominio real
- [ ] PostgreSQL configurado (`DATABASE_URL`)
- [ ] Email (`EMAIL_HOST_PASSWORD`) probado
- [ ] `DNI_API_TOKEN` (Decolecta) o token guardado en **Seguridad → Config. API DNI**
- [ ] `NEO_ADMIN_PASSWORD` segura (usuario **Neo**)
- [ ] Certificado SSL activo
- [ ] Carpeta `media/` con plantillas de contrato/constancia
- [ ] Backup de `db/` o snapshot de la base gestionada

## Generar SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```
