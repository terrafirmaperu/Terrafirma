import time

from crum import get_current_request
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator

from config import settings
from core.security.models import GroupPermission, Module
from core.security.role_groups import user_has_supervisor_access

PERMISSION_DENIED_MSG = 'No tiene permiso para ingresar a este módulo'


def user_bypasses_group_permissions(user):
    return user_has_supervisor_access(user)


def _module_for_permission(codename, request_path=''):
    gp = (
        GroupPermission.objects.filter(permission__codename=codename)
        .select_related('module')
        .first()
    )
    if gp:
        return gp.module
    if not request_path:
        return None
    path = request_path if request_path.endswith('/') else request_path + '/'
    for module in Module.objects.filter(is_active=True).order_by('-url'):
        url = module.url or ''
        if url and path.startswith(url):
            return module
    return None


def _permission_denied_response(request):
    messages.error(request, PERMISSION_DENIED_MSG)
    request.session.pop('url_last', None)
    request.session.modified = True
    if request.method == 'POST':
        return JsonResponse({'error': PERMISSION_DENIED_MSG}, status=403)
    return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

SUPERVISOR_DELETE_SESSION_KEY = 'supervisor_delete_approved_at'
SUPERVISOR_PREDIO_UNLOCK_SESSION_KEY = 'supervisor_predio_unlock_approved_at'
SUPERVISOR_COLLECTOR_SESSION_KEY = 'supervisor_collector_approved_at'
SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY = 'supervisor_collector_save_approved_at'
SUPERVISOR_QUOTA_EDIT_SESSION_KEY = 'supervisor_quota_edit_approved_at'
SUPERVISOR_DELETE_WINDOW_SEC = 180
SUPERVISOR_PREDIO_UNLOCK_WINDOW_SEC = 180
SUPERVISOR_COLLECTOR_WINDOW_SEC = 1800
SUPERVISOR_COLLECTOR_SAVE_WINDOW_SEC = 180
SUPERVISOR_QUOTA_EDIT_WINDOW_SEC = 180


def _consume_supervisor_approval(request, session_key, window_sec):
    ts = request.session.get(session_key)
    now = time.time()
    if ts is None:
        return False, 'Autorización del supervisor requerida.'
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        return False, 'Autorización inválida.'
    if now - ts > window_sec:
        return False, 'La autorización del supervisor expiró. Vuelva a intentar.'
    del request.session[session_key]
    request.session.modified = True
    return True, None


def consume_supervisor_predio_unlock(request):
    return _consume_supervisor_approval(
        request,
        SUPERVISOR_PREDIO_UNLOCK_SESSION_KEY,
        SUPERVISOR_PREDIO_UNLOCK_WINDOW_SEC,
    )


def consume_supervisor_quota_edit(request):
    return _consume_supervisor_approval(
        request,
        SUPERVISOR_QUOTA_EDIT_SESSION_KEY,
        SUPERVISOR_QUOTA_EDIT_WINDOW_SEC,
    )


def _supervisor_session_valid(request, session_key, window_sec):
    if user_has_supervisor_access(request.user):
        return True
    ts = request.session.get(session_key)
    if ts is None:
        return False
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        return False
    return time.time() - ts <= window_sec


class SupervisorCollectorMixin(object):
    """Admin Cobranzas: solo superusuario (Neo) o quien autorice con su contraseña."""

    supervisor_collector_gate_template = 'frm/collector/supervisor_gate.html'

    def _collector_supervisor_ok(self, request):
        return _supervisor_session_valid(
            request,
            SUPERVISOR_COLLECTOR_SESSION_KEY,
            SUPERVISOR_COLLECTOR_WINDOW_SEC,
        )

    def render_supervisor_gate(self, request):
        from django.shortcuts import render
        return render(
            request,
            self.supervisor_collector_gate_template,
            {
                'title': 'Admin Cobranzas',
                'next_url': request.get_full_path(),
            },
        )

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not self._collector_supervisor_ok(request):
            if request.method == 'POST':
                return JsonResponse(
                    {'error': 'Autorización del supervisor requerida (usuario Neo o contraseña de superusuario).'},
                    status=403,
                )
            return self.render_supervisor_gate(request)
        return super().dispatch(request, *args, **kwargs)


def require_supervisor_collector_save(request):
    if user_has_supervisor_access(request.user):
        return None
    ok, err = _consume_supervisor_approval(
        request,
        SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY,
        SUPERVISOR_COLLECTOR_SAVE_WINDOW_SEC,
    )
    if ok:
        return None
    return JsonResponse(
        {
            'error': err or 'Autorización del supervisor requerida para registrar cobradores.',
        },
        status=403,
    )


class ModuleMixin(object):

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        from core.security.session_group import set_module_id_in_session
        set_module_id_in_session(request, None)
        try:
            request.user.set_group_session()
            if user_bypasses_group_permissions(request.user):
                module = Module.objects.filter(is_active=True, url=request.path).first()
                if module:
                    set_module_id_in_session(request, module)
                return super().get(request, *args, **kwargs)
            group_id = request.user.get_group_id_session()
            modules = Module.objects.filter(
                Q(moduletype__is_active=True) | Q(moduletype__isnull=True),
            ).filter(
                groupmodule__group_id__in=[group_id],
                is_active=True,
                url=request.path,
                is_visible=True,
            )
            if modules.exists():
                set_module_id_in_session(request, modules[0])
                return super().get(request, *args, **kwargs)
            return _permission_denied_response(request)
        except Exception:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)


class PermissionMixin(object):
    permission_required = None

    def get_permits(self):
        pr = self.permission_required
        if pr is None:
            return []
        if isinstance(pr, str):
            return [pr]
        if isinstance(pr, (list, tuple, set, frozenset)):
            return list(pr)
        raise TypeError(
            '{}.permission_required must be str or iterable of str, not {}'.format(
                self.__class__.__name__,
                type(pr).__name__,
            )
        )

    def get_last_url(self):
        request = get_current_request()
        if 'url_last' in request.session:
            return request.session['url_last']
        return settings.LOGIN_REDIRECT_URL

    def _permission_granted(self, request):
        if user_bypasses_group_permissions(request.user):
            return True
        from core.security.session_group import get_group_from_session
        group = get_group_from_session(request)
        if group is None:
            return False
        permits = self.get_permits()
        if not permits:
            return True
        for codename in permits:
            if not group.grouppermission_set.filter(permission__codename=codename).exists():
                return False
        return True

    def _bind_module_session(self, request):
        from core.security.session_group import get_group_from_session, set_module_id_in_session
        permits = self.get_permits()
        if not permits:
            return
        if user_bypasses_group_permissions(request.user):
            module = _module_for_permission(permits[0], request.path)
            if module:
                set_module_id_in_session(request, module)
            request.session['url_last'] = request.path
            request.session.modified = True
            return
        group = get_group_from_session(request)
        if group is None:
            return
        grouppermission = group.grouppermission_set.filter(
            permission__codename=permits[0],
        ).select_related('module').first()
        if grouppermission:
            request.session['url_last'] = request.path
            set_module_id_in_session(request, grouppermission.module)
            request.session.modified = True

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        from core.security.session_group import set_module_id_in_session
        set_module_id_in_session(request, None)
        try:
            request.user.set_group_session()
            if not self._permission_granted(request):
                return _permission_denied_response(request)
            self._bind_module_session(request)
            return super().dispatch(request, *args, **kwargs)
        except Exception:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SupervisorDeleteApprovalMixin(object):
    """Exige autorización reciente de un superusuario antes de procesar POST (eliminar)."""

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST' and not user_has_supervisor_access(request.user):
            ts = request.session.get(SUPERVISOR_DELETE_SESSION_KEY)
            now = time.time()
            if ts is None:
                return JsonResponse(
                    {'error': 'Autorización del supervisor requerida.'},
                    status=403,
                )
            try:
                ts = float(ts)
            except (TypeError, ValueError):
                return JsonResponse({'error': 'Autorización inválida.'}, status=403)
            if now - ts > SUPERVISOR_DELETE_WINDOW_SEC:
                return JsonResponse(
                    {'error': 'La autorización del supervisor expiró. Vuelva a intentar.'},
                    status=403,
                )
            from core.security.supervisor_audit import (
                describe_deleted_object,
                log_supervisor_event,
                pop_supervisor_authorizer,
            )
            supervisor = pop_supervisor_authorizer(request, SUPERVISOR_DELETE_SESSION_KEY)
            deleted_obj = None
            try:
                deleted_obj = self.get_object()
            except Exception:
                deleted_obj = None
            change = describe_deleted_object(deleted_obj)
            if deleted_obj is None:
                change = 'Eliminó registro id={} ({})'.format(
                    kwargs.get('pk', '—'),
                    self.__class__.__name__,
                )
            log_supervisor_event(
                request,
                'action_delete',
                category='accion',
                detail='Ruta: {} · Vista: {}'.format(request.path, self.__class__.__name__),
                change_summary='Eliminó: {}'.format(change),
                supervisor_user=supervisor,
                object_type=deleted_obj.__class__.__name__ if deleted_obj else self.__class__.__name__,
                object_id=getattr(deleted_obj, 'pk', kwargs.get('pk', '')),
            )
            del request.session[SUPERVISOR_DELETE_SESSION_KEY]
            request.session.modified = True
        return super().dispatch(request, *args, **kwargs)
