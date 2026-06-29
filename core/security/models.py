import os
from datetime import *

from crum import get_current_request
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.forms.models import model_to_dict

from config import settings
from core.security.choices import *
from core.user.models import User


class Dashboard(models.Model):
    name = models.CharField(verbose_name='Nombre', max_length=50, unique=True)
    image = models.ImageField(verbose_name='Logo', upload_to='dashboard/%Y/%m/%d', null=True, blank=True)
    icon = models.CharField(max_length=500, verbose_name='Icono FontAwesome')
    layout = models.IntegerField(default=1, verbose_name='Diseño', blank=True, null=True, choices=layout_options)
    card = models.CharField(max_length=50, verbose_name='Card', choices=card, default=card[0][0])
    navbar = models.CharField(max_length=50, verbose_name='Navbar', choices=navbar, default=navbar[0][0])
    brand_logo = models.CharField(max_length=50, verbose_name='Brand Logo', choices=brand_logo,
                                  default=brand_logo[0][0])
    sidebar = models.CharField(max_length=50, verbose_name='Sidebar', choices=sidebar, default=sidebar[0][0])

    def __str__(self):
        return self.name

    def get_icon(self):
        if self.icon:
            return self.icon
        return 'fa fa-cubes'

    def get_image(self):
        if self.image:
            return '{}{}'.format(settings.MEDIA_URL, self.image)
        return '{}{}'.format(settings.STATIC_URL, 'img/default/empty.png')

    def remove_image(self):
        try:
            if self.image:
                os.remove(self.image.path)
        except:
            pass
        finally:
            self.image = None

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Dashboard'
        verbose_name_plural = 'Dashboards'
        default_permissions = ()
        permissions = (
            ('view_dashboard', 'Can view Dashboard'),
        )
        ordering = ['-id']


class ModuleType(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='Nombre')
    icon = models.CharField(max_length=100, unique=True, verbose_name='Icono')
    is_active = models.BooleanField(default=True, verbose_name='Estado')

    def __str__(self):
        return self.name

    def get_modules_vertical(self):
        try:
            request = get_current_request()
            if request is None:
                return self.module_set.none()
            from core.security.session_group import get_group_from_session

            group = get_group_from_session(request)
            group_id = group.pk if group else request.user.get_group_id_session()
            if group_id:
                return self.module_set.filter(
                    is_active=True,
                    is_vertical=True,
                    is_visible=True,
                    groupmodule__group_id=group_id,
                ).order_by('name')
        except Exception:
            pass
        return self.module_set.none()

    def get_modules_horizontal(self):
        try:
            request = get_current_request()
            if request is None:
                return self.module_set.none()
            from core.security.session_group import get_group_from_session

            group = get_group_from_session(request)
            group_id = group.pk if group else request.user.get_group_id_session()
            if group_id:
                return self.module_set.filter(
                    is_active=True,
                    is_vertical=False,
                    is_visible=True,
                    groupmodule__group_id=group_id,
                ).order_by('name')
        except Exception:
            pass
        return self.module_set.none()

    def toJSON(self):
        item = model_to_dict(self)
        item['icon'] = self.get_icon()
        return item

    def get_icon(self):
        if self.icon:
            return self.icon
        return 'fa fa-times'

    class Meta:
        verbose_name = 'Tipo de Módulo'
        verbose_name_plural = 'Tipos de Módulos'
        ordering = ['-name']


class Module(models.Model):
    url = models.CharField(max_length=100, verbose_name='Url', unique=True)
    name = models.CharField(max_length=100, verbose_name='Nombre')
    moduletype = models.ForeignKey(ModuleType, null=True, blank=True, verbose_name='Tipo de Módulo',
                                   on_delete=models.PROTECT)
    description = models.CharField(max_length=200, null=True, blank=True, verbose_name='Descripción')
    icon = models.CharField(max_length=100, verbose_name='Icono', null=True, blank=True)
    image = models.ImageField(upload_to='module/%Y/%m/%d', verbose_name='Imagen', null=True, blank=True)
    is_vertical = models.BooleanField(default=False, verbose_name='Vertical')
    is_active = models.BooleanField(default=True, verbose_name='Estado')
    is_visible = models.BooleanField(default=True, verbose_name='Visible')
    permits = models.ManyToManyField(Permission, verbose_name='Permisos', blank=True)

    def __str__(self):
        return '{} [{}]'.format(self.name, self.url)

    def toJSON(self):
        item = model_to_dict(self)
        item['icon'] = self.get_icon()
        item['moduletype'] = {} if self.moduletype is None else self.moduletype.toJSON()
        item['icon'] = self.get_icon()
        item['image'] = self.get_image()
        item['permits'] = [{'id': p.id, 'name': p.name, 'codename': p.codename, 'state': 0} for p in self.permits.all()]
        return item

    def get_icon(self):
        if self.icon:
            return self.icon
        return 'fa fa-times'

    def get_image(self):
        if self.image:
            return '{}{}'.format(settings.MEDIA_URL, self.image)
        return '{}{}'.format(settings.STATIC_URL, 'img/default/empty.png')

    def get_image_icon(self):
        if self.image:
            return self.get_image()
        if self.icon:
            return self.get_icon()
        return '{}{}'.format(settings.STATIC_URL, 'img/default/empty.png')

    def get_moduletype(self):
        if self.moduletype:
            return self.moduletype.name
        return None

    def delete(self, using=None, keep_parents=False):
        try:
            os.remove(self.image.path)
        except:
            pass
        super(Module, self).delete()

    class Meta:
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'
        ordering = ['-name']


class GroupModule(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.PROTECT)

    def __str__(self):
        return self.module.name

    class Meta:
        verbose_name = 'Grupo Módulo'
        verbose_name_plural = 'Grupos Módulos'
        default_permissions = ()
        ordering = ['-id']


class GroupPermission(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.PROTECT)
    module = models.ForeignKey(Module, on_delete=models.PROTECT)

    def __str__(self):
        return self.module.name

    class Meta:
        verbose_name = 'Grupo Permiso'
        verbose_name_plural = 'Grupos Permisos'
        default_permissions = ()
        ordering = ['-id']


class DatabaseBackups(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_joined = models.DateField(default=datetime.now)
    hour = models.TimeField(default=datetime.now)
    localhost = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=150, null=True, blank=True)
    archive = models.FileField(upload_to='backup/%Y/%m/%d')

    def __str__(self):
        return self.location

    def toJSON(self):
        item = model_to_dict(self)
        item['user'] = self.user.toJSON()
        item['date_joined'] = self.date_joined.strftime('%d-%m-%Y')
        item['hour'] = self.hour.strftime('%H:%M %p')
        item['archive'] = self.get_archive()
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        try:
            request = get_current_request()
            self.location = request.session['infobyip'].get('location')
            self.localhost = request.session['infobyip'].get('ipaddress')
        except:
            self.localhost = None
        super(DatabaseBackups, self).save()

    def get_archive(self):
        if self.archive:
            return '{}{}'.format(settings.MEDIA_URL, self.archive)
        return ''

    def delete(self, using=None, keep_parents=False):
        try:
            os.remove(self.archive.path)
        except:
            pass
        super(DatabaseBackups, self).delete()

    class Meta:
        verbose_name_plural = 'Respaldo de BD'
        verbose_name = 'Respaldos de BD'
        default_permissions = ()
        permissions = (
            ('view_databasebackups', 'Can view Respaldos de BD'),
            ('add_databasebackups', 'Can add Respaldos de BD'),
            ('delete_databasebackups', 'Can delete Respaldos de BD'),
        )
        ordering = ['-id']


class AccessUsers(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_joined = models.DateField(default=datetime.now)
    hour = models.TimeField(default=datetime.now)
    localhost = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return self.location

    def toJSON(self):
        item = model_to_dict(self)
        item['user'] = self.user.toJSON()
        item['date_joined'] = self.date_joined.strftime('%d-%m-%Y')
        item['hour'] = self.hour.strftime('%H:%M %p')
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        try:
            request = get_current_request()
            self.location = request.session['infobyip'].get('location')
            self.localhost = request.session['infobyip'].get('ipaddress')
        except:
            self.localhost = None
        super(AccessUsers, self).save()

    class Meta:
        verbose_name = 'Acceso del usuario'
        verbose_name_plural = 'Accesos de los usuarios'
        default_permissions = ()
        permissions = (
            ('view_accessusers', 'Can view Acceso del usuario'),
            ('delete_accessusers', 'Can delete Acceso del usuario'),
        )
        ordering = ['-id']


class DniApiConfiguration(models.Model):
    """Configuración singleton del proveedor de consulta DNI (RENIEC)."""

    DEFAULT_API_URL = 'https://api.decolecta.com/v1/reniec/dni?numero={dni}'

    provider_name = models.CharField(
        max_length=80,
        default='Decolecta',
        verbose_name='Proveedor',
    )
    api_url = models.CharField(
        max_length=500,
        default=DEFAULT_API_URL,
        verbose_name='URL de consulta',
        help_text='Use {dni} donde va el número de documento.',
    )
    api_token = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='API Key / Token',
    )
    api_timeout = models.PositiveSmallIntegerField(
        default=12,
        verbose_name='Tiempo de espera (segundos)',
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name='Consulta DNI habilitada',
    )
    notes = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='Notas',
    )

    def __str__(self):
        return self.provider_name or 'Configuración API DNI'

    def token_configured(self):
        return bool((self.api_token or '').strip())

    def toJSON(self):
        item = model_to_dict(self)
        item['token_configured'] = self.token_configured()
        item['api_token'] = '********' if self.token_configured() else ''
        return item

    @classmethod
    def get_solo(cls):
        row = cls.objects.order_by('id').first()
        if row:
            return row
        return cls(
            provider_name='Decolecta',
            api_url=cls.DEFAULT_API_URL,
            api_timeout=12,
            is_enabled=True,
        )

    class Meta:
        verbose_name = 'Configuración API DNI'
        verbose_name_plural = 'Configuración API DNI'
        default_permissions = ()
        permissions = (
            ('view_dniapiconfiguration', 'Can view Configuración API DNI'),
            ('change_dniapiconfiguration', 'Can change Configuración API DNI'),
        )


class SupervisorAuditLog(models.Model):
    CATEGORY_CHOICES = (
        ('autorizacion', 'Autorización'),
        ('accion', 'Acción'),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha y hora')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='accion')
    event_type = models.CharField(max_length=60, verbose_name='Tipo')
    summary = models.CharField(max_length=255, verbose_name='Resumen')
    detail = models.TextField(blank=True, default='', verbose_name='Detalle')
    actor_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervisor_audit_actions',
        verbose_name='Usuario en sesión',
    )
    supervisor_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervisor_audit_authorizations',
        verbose_name='Supervisor autorizó',
    )
    ip_address = models.CharField(max_length=45, blank=True, default='')
    request_path = models.CharField(max_length=500, blank=True, default='')
    object_type = models.CharField(max_length=120, blank=True, default='')
    object_id = models.CharField(max_length=80, blank=True, default='')
    change_summary = models.TextField(
        blank=True,
        default='',
        verbose_name='Cambio realizado',
    )

    def get_event_type_display_label(self):
        from core.security.supervisor_audit import EVENT_LABELS
        return EVENT_LABELS.get(self.event_type, self.event_type)

    def __str__(self):
        return '{} — {}'.format(self.created_at, self.summary)

    class Meta:
        verbose_name = 'Registro supervisor'
        verbose_name_plural = 'Registros supervisor'
        ordering = ['-created_at', '-id']
        default_permissions = ()
