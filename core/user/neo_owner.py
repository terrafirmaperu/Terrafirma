# -*- coding: utf-8 -*-
"""Neo: dueño/desarrollador con acceso total al ERP."""

import os

from django.contrib.auth import get_user_model

NEO_USERNAME = 'Neo'
DEFAULT_NEO_PASSWORD = 'lafamilia123456789'


def neo_password(explicit=None):
    if explicit:
        return explicit
    return (
        os.environ.get('NEO_ADMIN_PASSWORD', '').strip()
        or DEFAULT_NEO_PASSWORD
    )


def ensure_neo_owner(password=None, *, sync_groups=True, reset_password=True):
    """Crea o actualiza Neo: superusuario activo, solo grupo Supervisor."""
    from core.security.role_groups import assign_supervisor_group_only, repair_supervisor_module_links, sync_all_role_groups

    User = get_user_model()
    pwd = neo_password(password)

    if sync_groups:
        sync_all_role_groups()

    defaults = {
        'dni': '0000000000001',
        'email': 'neo@factora.local',
        'first_name': 'Supervisor',
        'last_name': 'Sistema',
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
        'is_change_password': False,
    }
    user, created = User.objects.update_or_create(username=NEO_USERNAME, defaults=defaults)
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.is_change_password = False
    if reset_password:
        user.set_password(pwd)
    user.save()

    assign_supervisor_group_only(user)
    repair_supervisor_module_links(user)
    return user, created
