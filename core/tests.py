import os

from config.wsgi import *
from core.security.models import *
from django.contrib.auth.models import Permission
from core.pos.models import *

dashboard, _created_dash = Dashboard.objects.get_or_create(
    name='Qori',
    defaults={
        'icon': 'fas fa-shopping-cart',
        'layout': 1,
        'card': ' ',
        'navbar': 'navbar-dark navbar-primary',
        'brand_logo': ' ',
        'sidebar': 'sidebar-light-primary',
    },
)

company = Company()
company.name = 'QORI TERRAFIRMA'
company.ruc = '20612888141'
company.email = 'naihtsircristhian@gmail.com'
company.phone = '921047681'
company.mobile = '921047681'
company.desc = 'ASESORIA EN PROCESOS DE TITULACIÓN'
company.website = 'terrafirmaperu.com'
company.address = 'AV. MANCHEGO MUÑOZ N° 496 - HUANCAVELICA'
company.igv = 18.00
company.save()

type = ModuleType()
type.name = 'Seguridad'
type.icon = 'fas fa-lock'
type.save()
mt_seguridad = type
print('insertado {}'.format(type.name))

module = Module()
module.moduletype = mt_seguridad
module.name = 'Tipos de Módulos'
module.url = '/security/module/type/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-door-open'
module.description = 'Permite administrar los tipos de módulos del sistema'
module.save()
for p in Permission.objects.filter(content_type__model=ModuleType._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_seguridad
module.name = 'Módulos'
module.url = '/security/module/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-th-large'
module.description = 'Permite administrar los módulos del sistema'
module.save()
for p in Permission.objects.filter(content_type__model=Module._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_seguridad
module.name = 'Grupos'
module.url = '/security/group/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-users'
module.description = 'Permite administrar los grupos de usuarios del sistema'
module.save()
for p in Permission.objects.filter(content_type__model=Group._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_seguridad
module.name = 'Respaldos'
module.url = '/security/database/backups/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-database'
module.description = 'Permite administrar los respaldos de base de datos'
module.save()
for p in Permission.objects.filter(content_type__model=DatabaseBackups._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_seguridad
module.name = 'Conf. Dashboard'
module.url = '/security/dashboard/update/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-tools'
module.description = 'Permite configurar los datos de la plantilla'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_seguridad
module.name = 'Config. API DNI'
module.url = '/security/api/dni/update/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-id-card'
module.description = 'API Key y URL para consulta RENIEC al registrar clientes'
module.save()
for p in Permission.objects.filter(content_type__model='dniapiconfiguration'):
    module.permits.add(p)
print('insertado {}'.format(module.name))

dni_cfg, _dni_created = DniApiConfiguration.objects.get_or_create(
    provider_name='Decolecta',
    defaults={
        'api_url': DniApiConfiguration.DEFAULT_API_URL,
        'api_timeout': 12,
        'is_enabled': True,
        'notes': 'Cuenta terrafirmaperu@gmail.com',
    },
)
if _dni_created:
    _env_token = (os.environ.get('DNI_API_TOKEN') or '').strip()
    if _env_token:
        dni_cfg.api_token = _env_token
        dni_cfg.save(update_fields=['api_token'])

module = Module()
module.moduletype = mt_seguridad
module.name = 'Accesos'
module.url = '/security/access/users/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-user-secret'
module.description = 'Permite administrar los accesos de los usuarios'
module.save()
for p in Permission.objects.filter(content_type__model=AccessUsers._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_seguridad
module.name = 'Usuarios'
module.url = '/user/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-user'
module.description = 'Permite administrar a los administradores del sistema'
module.save()
for p in Permission.objects.filter(content_type__model=User._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

type = ModuleType()
type.name = 'Bodega'
type.icon = 'fas fa-boxes'
type.save()
mt_bodega = type
print('insertado {}'.format(type.name))

module = Module()
module.moduletype = mt_bodega
module.name = 'Categorías'
module.url = '/pos/scm/category/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-truck-loading'
module.description = 'Permite administrar las categorías de los productos'
module.save()
for p in Permission.objects.filter(content_type__model=Category._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_bodega
module.name = 'Productos'
module.url = '/pos/scm/product/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-box'
module.description = 'Permite administrar los productos del sistema'
module.save()
for p in Permission.objects.filter(content_type__model=Product._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_bodega
module.name = 'Compras'
module.url = '/pos/scm/purchase/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-dolly-flatbed'
module.description = 'Permite administrar las compras de los productos'
module.save()
for p in Permission.objects.filter(content_type__model=Purchase._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

'''module = Module()
module.moduletype = mt_bodega
module.name = 'Ajuste de Stock'
module.url = '/pos/scm/product/stock/adjustment/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-sliders-h'
module.description = 'Permite administrar los ajustes de stock de productos'
module.save()
print('insertado {}'.format(module.name))'''

type = ModuleType()
type.name = 'Administrativo'
type.icon = 'fas fa-hand-holding-usd'
type.save()
mt_administrativo = type
print('insertado {}'.format(type.name))

module = Module()
module.moduletype = mt_administrativo
module.name = 'Tipos de Gastos'
module.url = '/pos/frm/type/expense/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-comments-dollar'
module.description = 'Permite administrar los tipos de gastos'
module.save()
for p in Permission.objects.filter(content_type__model=TypeExpense._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_administrativo
module.name = 'Gastos'
module.url = '/pos/frm/expenses/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-file-invoice-dollar'
module.description = 'Permite administrar los gastos de la compañia'
module.save()
for p in Permission.objects.filter(content_type__model=Expenses._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_administrativo
module.name = 'Caja'
module.url = '/pos/frm/cash/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-cash-register'
module.description = 'Permite administrar las sesiones de caja (apertura y cierre)'
module.save()
for p in Permission.objects.filter(content_type__model=CashRegisterSession._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_administrativo
module.name = 'Cuentas por cobrar'
module.url = '/pos/frm/ctas/collect/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-funnel-dollar'
module.description = 'Permite administrar las cuentas por cobrar de los clientes'
module.save()
for p in Permission.objects.filter(content_type__model=CtasCollect._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_administrativo
module.name = 'Admin Cobranzas'
module.url = '/pos/frm/collector/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-user-tag'
module.description = 'Registro de cobradores asignados a ventas al crédito'
module.save()
for p in Permission.objects.filter(content_type__model=Collector._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

'''module = Module()
module.moduletype = mt_administrativo
module.name = 'Cuentas por pagar'
module.url = '/pos/frm/debts/pay/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-money-check-alt'
module.description = 'Permite administrar las cuentas por pagar de los proveedores'
module.save()
for p in Permission.objects.filter(content_type__model=DebtsPay._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))'''

type = ModuleType()
type.name = 'Facturación'
type.icon = 'fas fa-calculator'
type.save()
mt_facturacion = type
print('insertado {}'.format(type.name))

module = Module()
module.moduletype = mt_facturacion
module.name = 'Clientes'
module.url = '/pos/crm/client/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-user-friends'
module.description = 'Permite administrar los clientes del sistema'
module.save()
for p in Permission.objects.filter(content_type__model=Client._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_facturacion
module.name = 'Ventas'
module.url = '/pos/crm/sale/admin/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-shopping-cart'
module.description = 'Permite administrar las ventas de los productos'
module.save()
for p in Permission.objects.filter(content_type__model=Sale._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.name = 'Ventas'
module.url = '/pos/crm/sale/client/'
module.is_active = True
module.is_vertical = False
module.is_visible = True
module.icon = 'fas fa-shopping-cart'
module.description = 'Permite administrar las ventas de los productos'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_facturacion
module.name = 'Promociones'
module.url = '/pos/crm/promotions/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'far fa-calendar-check'
module.description = 'Permite administrar las promociones de los productos'
module.save()
for p in Permission.objects.filter(content_type__model=Promotions._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_facturacion
module.name = 'Devoluciones'
module.url = '/pos/crm/devolution/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-exchange-alt'
module.description = 'Permite administrar las devoluciones de los productos'
module.save()
for p in Permission.objects.filter(content_type__model=Devolution._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_facturacion
module.name = 'Control de Avance Asesoría'
module.url = '/pos/crm/advisory/progress/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-route'
module.description = 'Etapas de saneamiento visibles en el portal del cliente (2 a 9 etapas)'
module.save()
for p in Permission.objects.filter(content_type__model=AdvisoryProgressCase._meta.label.split('.')[1].lower()):
    module.permits.add(p)
print('insertado {}'.format(module.name))

type = ModuleType()
type.name = 'Reportes'
type.icon = 'fas fa-chart-pie'
type.save()
mt_reportes = type
print('insertado {}'.format(type.name))

module = Module()
module.moduletype = mt_reportes
module.name = 'Ventas'
module.url = '/reports/sale/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-chart-bar'
module.description = 'Permite ver los reportes de las ventas'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_reportes
module.name = 'Compras'
module.url = '/reports/purchase/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-chart-bar'
module.description = 'Permite ver los reportes de las compras'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_reportes
module.name = 'Gastos'
module.url = '/reports/expenses/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-chart-bar'
module.description = 'Permite ver los reportes de los gastos'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_reportes
module.name = 'Cuentas por Pagar'
module.url = '/reports/debts/pay/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-chart-bar'
module.description = 'Permite ver los reportes de las cuentas por pagar'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_reportes
module.name = 'Cuentas por Cobrar'
module.url = '/reports/ctas/collect/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-chart-bar'
module.description = 'Permite ver los reportes de las cuentas por cobrar'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_reportes
module.name = 'Perdidas y Ganacias'
module.url = '/reports/results/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-chart-bar'
module.description = 'Permite ver los reportes de perdidas y ganancias'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.moduletype = mt_reportes
module.name = 'Clientes'
module.url = '/reports/clients/'
module.is_active = True
module.is_vertical = True
module.is_visible = True
module.icon = 'fas fa-users'
module.description = 'Listado de clientes con filtros por comunidad, centro poblado, provincia y distrito'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.name = 'Cambiar password'
module.url = '/user/update/password/'
module.is_active = True
module.is_vertical = False
module.is_visible = True
module.icon = 'fas fa-key'
module.description = 'Permite cambiar tu password de tu cuenta'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.name = 'Editar perfil'
module.url = '/user/update/profile/'
module.is_active = True
module.is_vertical = False
module.is_visible = True
module.icon = 'fas fa-user'
module.description = 'Permite cambiar la información de tu cuenta'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.name = 'Editar perfil'
module.url = '/pos/crm/client/update/profile/'
module.is_active = True
module.is_vertical = False
module.is_visible = True
module.icon = 'fas fa-user'
module.description = 'Permite cambiar la información de tu cuenta'
module.save()
print('insertado {}'.format(module.name))

module = Module()
module.name = 'Compañia'
module.url = '/pos/crm/company/update/'
module.is_active = True
module.is_vertical = False
module.is_visible = True
module.icon = 'fas fa-building'
module.description = 'Permite gestionar la información de la compañia'
module.save()
print('insertado {}'.format(module.name))

group = Group()
group.name = 'Administrador'
group.save()
print('insertado {}'.format(group.name))
for m in Module.objects.filter().exclude(url__in=['/pos/crm/client/update/profile/', '/pos/crm/sale/client/']):
    gm = GroupModule()
    gm.module = m
    gm.group = group
    gm.save()
    for perm in m.permits.all():
        group.permissions.add(perm)
        grouppermission = GroupPermission()
        grouppermission.module_id = m.id
        grouppermission.group_id = group.id
        grouppermission.permission_id = perm.id
        grouppermission.save()

group = Group()
group.name = 'Cliente'
group.save()
print('insertado {}'.format(group.name))
for m in Module.objects.filter(url__in=['/pos/crm/client/update/profile/', '/pos/crm/sale/client/', '/user/update/password/']).exclude():
    gm = GroupModule()
    gm.module = m
    gm.group = group
    gm.save()

u, _created_neo = User.objects.update_or_create(
    username='Neo',
    defaults={
        'first_name': 'Cristhian Plinio',
        'last_name': 'CHANCHA CALDERON',
        'dni': '46200203',
        'email': 'seo.cristhian@gmail.com',
        'is_active': True,
        'is_superuser': True,
        'is_staff': True,
    },
)
_neo_pwd = os.environ.get('NEO_ADMIN_PASSWORD', '').strip() or 'Enyaeslamejor'
u.set_password(_neo_pwd)
u.is_active = True
u.is_staff = True
u.is_superuser = True
u.save()
group = Group.objects.filter(name='Administrador').first() or Group.objects.order_by('pk').first()
if group:
    u.groups.add(group)
