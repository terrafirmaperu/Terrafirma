# -*- coding: utf-8 -*-
"""Grupos predeterminados: Supervisor, Administrador y Asistente."""

from django.contrib.auth.models import Group, Permission

from core.security.models import GroupModule, GroupPermission, Module

GROUP_SUPERVISOR = 'Supervisor'
GROUP_ADMINISTRADOR = 'Administrador'
GROUP_ASISTENTE = 'Asistente'

DEFAULT_USER_GROUP_NAMES = (
    GROUP_SUPERVISOR,
    GROUP_ADMINISTRADOR,
    GROUP_ASISTENTE,
    'Cliente',
)

CLIENT_ONLY_URLS = (
    '/pos/crm/client/update/profile/',
    '/pos/crm/sale/client/',
    '/user/update/password/',
)

# Mensajería WhatsApp: solo Supervisor (Configuraciones + Mensajes).
MENSAJERIA_MODULE_TYPE = 'Mensajería'
MENSAJERIA_MODULE_URLS = (
    '/whatsapp/config/',
    '/whatsapp/messages/',
)

# Asistente: vender, cobrar y operar caja; sin Seguridad, Reportes ni Bodega.
ASISTENTE_MODULE_URLS = (
    '/pos/frm/cash/',
    '/pos/frm/ctas/collect/',
    '/pos/crm/sale/admin/',
    '/pos/crm/client/',
    '/user/update/password/',
)

# Permisos de escritura permitidos al Asistente (además de view_*).
ASISTENTE_WRITE_CODENAMES = frozenset({
    'add_sale',
    'add_client',
    'add_ctascollect',
    'add_cashregistersession',
    'change_cashregistersession',
})


def _clear_group_access(group):
    group.grouppermission_set.all().delete()
    group.groupmodule_set.all().delete()
    group.permissions.clear()


def _link_module_permissions(group, module, permission_filter=None):
    GroupModule.objects.get_or_create(group=group, module=module)
    for perm in module.permits.all():
        if permission_filter is not None and not permission_filter(perm):
            continue
        group.permissions.add(perm)
        GroupPermission.objects.get_or_create(
            group=group,
            module=module,
            permission=perm,
        )


def _view_only(perm):
    return perm.codename.startswith('view_')


def _asistente_perm(perm):
    if perm.codename.startswith('view_'):
        return True
    return perm.codename in ASISTENTE_WRITE_CODENAMES


def _business_modules_qs():
    return Module.objects.filter(is_active=True).exclude(url__in=CLIENT_ONLY_URLS)


def user_has_supervisor_access(user):
    """Supervisor o superusuario: acceso total al ERP."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return user.groups.filter(name=GROUP_SUPERVISOR).exists()


def sync_supervisor_group():
    """Acceso total a todos los módulos activos del ERP."""
    group = Group.objects.filter(name=GROUP_SUPERVISOR).first()
    if group is None:
        group = Group.objects.create(name=GROUP_SUPERVISOR)
    _clear_group_access(group)
    for module in Module.objects.filter(is_active=True):
        _link_module_permissions(group, module)
    group.permissions.set(Permission.objects.all())
    return group


def sync_administrador_group():
    """
    Igual que Asistente en ventas/cobros/caja/clientes.
    Además consulta (view_*) el resto del negocio sin Seguridad.
    Cambios que exigen contraseña de Neo siguen bloqueados por el sistema.
    """
    group = Group.objects.filter(name=GROUP_ADMINISTRADOR).first()
    if group is None:
        group = Group.objects.create(name=GROUP_ADMINISTRADOR)
    _clear_group_access(group)

    for module in Module.objects.filter(is_active=True, url__in=ASISTENTE_MODULE_URLS):
        _link_module_permissions(group, module, _asistente_perm)

    other = (
        _business_modules_qs()
        .exclude(moduletype__name='Seguridad')
        .exclude(moduletype__name=MENSAJERIA_MODULE_TYPE)
        .exclude(url__in=ASISTENTE_MODULE_URLS)
        .exclude(url__in=MENSAJERIA_MODULE_URLS)
    )
    for module in other:
        _link_module_permissions(group, module, _view_only)
    return group


def sync_asistente_group():
    """Ventas, cobranzas y caja; sin Seguridad, Reportes ni Bodega."""
    group = Group.objects.filter(name=GROUP_ASISTENTE).first()
    if group is None:
        group = Group.objects.create(name=GROUP_ASISTENTE)
    _clear_group_access(group)
    for module in Module.objects.filter(
        is_active=True,
        url__in=ASISTENTE_MODULE_URLS,
    ).exclude(url__in=MENSAJERIA_MODULE_URLS):
        _link_module_permissions(group, module, _asistente_perm)
    return group


def sync_all_role_groups():
    return {
        GROUP_SUPERVISOR: sync_supervisor_group(),
        GROUP_ADMINISTRADOR: sync_administrador_group(),
        GROUP_ASISTENTE: sync_asistente_group(),
    }


def assign_supervisor_group_only(user):
    """Deja al usuario solo en el grupo Supervisor (acceso total por módulos)."""
    if not user:
        return False
    supervisor = Group.objects.filter(name=GROUP_SUPERVISOR).first()
    if not supervisor:
        return False
    user.groups.set([supervisor])
    return True


def repair_supervisor_module_links(user):
    """Garantiza módulos vinculados al Supervisor (Neo / superusuario)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return

    is_owner = bool(getattr(user, 'is_superuser', False)) or getattr(user, 'username', '') == 'Neo'
    if not is_owner:
        return

    if not Module.objects.filter(is_active=True).exists():
        from django.core.management import call_command
        call_command('ensure_role_groups', verbosity=0)

    sync_supervisor_group()
    assign_supervisor_group_only(user)


def panel_module_types_for_group(group):
    """Tipos de módulo visibles en el panel para un grupo."""
    from core.security.models import ModuleType

    if not group:
        return ModuleType.objects.none()
    return (
        ModuleType.objects.filter(
            is_active=True,
            module__is_active=True,
            module__is_vertical=True,
            module__is_visible=True,
            module__groupmodule__group_id=group.pk,
        )
        .exclude(name='Mensajería')
        .distinct()
        .order_by('id')
    )
