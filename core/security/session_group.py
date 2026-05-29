"""Sesión compatible con JSONSerializer (IDs, no modelos Django en sesión)."""

from django.contrib.auth.models import Group

from core.security.models import Module


def get_group_from_session(request):
    if request is None:
        return None
    gid = request.session.get('group_id')
    if gid is not None:
        try:
            return Group.objects.get(pk=int(gid))
        except (Group.DoesNotExist, TypeError, ValueError):
            return None
    legacy = request.session.get('group')
    if legacy is not None and hasattr(legacy, 'pk'):
        return legacy
    return None


def set_group_id_in_session(request, group):
    if group is None:
        request.session.pop('group_id', None)
        request.session.pop('group', None)
    else:
        request.session['group_id'] = group.pk
        request.session.pop('group', None)
    request.session.modified = True


def get_module_from_session(request):
    if request is None:
        return None
    mid = request.session.get('module_id')
    if mid is not None:
        try:
            return Module.objects.get(pk=int(mid))
        except (Module.DoesNotExist, TypeError, ValueError):
            return None
    legacy = request.session.get('module')
    if legacy is not None and hasattr(legacy, 'pk'):
        return legacy
    return None


def set_module_id_in_session(request, module):
    if module is None:
        request.session.pop('module_id', None)
        request.session.pop('module', None)
    else:
        request.session['module_id'] = module.pk
        request.session.pop('module', None)
    request.session.modified = True


def auth_group(request):
    return {
        'session_group': get_group_from_session(request),
        'session_module': get_module_from_session(request),
    }
