import time

from crum import get_current_request
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator

from config import settings
from core.security.models import Module

SUPERVISOR_DELETE_SESSION_KEY = 'supervisor_delete_approved_at'
SUPERVISOR_PREDIO_UNLOCK_SESSION_KEY = 'supervisor_predio_unlock_approved_at'
SUPERVISOR_COLLECTOR_SESSION_KEY = 'supervisor_collector_approved_at'
SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY = 'supervisor_collector_save_approved_at'
SUPERVISOR_DELETE_WINDOW_SEC = 180
SUPERVISOR_PREDIO_UNLOCK_WINDOW_SEC = 180
SUPERVISOR_COLLECTOR_WINDOW_SEC = 1800
SUPERVISOR_COLLECTOR_SAVE_WINDOW_SEC = 180


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


def _supervisor_session_valid(request, session_key, window_sec):
    if getattr(request.user, 'is_superuser', False):
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
    if getattr(request.user, 'is_superuser', False):
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
            group_id = request.user.get_group_id_session()
            modules = Module.objects.filter(Q(moduletype__is_active=True) | Q(moduletype__isnull=True)).filter(
                groupmodule__group_id__in=[group_id], is_active=True, url=request.path, is_visible=True)
            if modules.exists():
                set_module_id_in_session(request, modules[0])
                return super().get(request, *args, **kwargs)
            else:
                messages.error(request, 'No tiene permiso para ingresar a este módulo')
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        except:
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

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        from core.security.session_group import get_group_from_session, set_module_id_in_session
        set_module_id_in_session(request, None)
        try:
            group = get_group_from_session(request)
            if group is not None:
                permits = self.get_permits()
                for p in permits:
                    if not group.grouppermission_set.filter(permission__codename=p).exists():
                        messages.error(request, 'No tiene permiso para ingresar a este módulo')
                        return HttpResponseRedirect(self.get_last_url())
                grouppermission = group.grouppermission_set.filter(permission__codename=permits[0])
                if grouppermission.exists():
                    request.session['url_last'] = request.path
                    set_module_id_in_session(request, grouppermission[0].module)
                return super().get(request, *args, **kwargs)
        except:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)


class SupervisorDeleteApprovalMixin(object):
    """Exige autorización reciente de un superusuario antes de procesar POST (eliminar)."""

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
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
            del request.session[SUPERVISOR_DELETE_SESSION_KEY]
            request.session.modified = True
        return super().dispatch(request, *args, **kwargs)
