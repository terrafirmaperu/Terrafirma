"""Sesión compatible con JSONSerializer (solo group_id, no el modelo Group)."""

from django.contrib.auth.models import Group


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


def auth_group(request):
    return {'session_group': get_group_from_session(request)}
