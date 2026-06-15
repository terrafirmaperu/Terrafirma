import time

from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from core.security.mixins import (
    SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY,
    SUPERVISOR_COLLECTOR_SESSION_KEY,
    SUPERVISOR_DELETE_SESSION_KEY,
    SUPERVISOR_PREDIO_UNLOCK_SESSION_KEY,
)
from core.security.supervisor_predio import user_can_authorize_predio_unlock


@method_decorator(require_POST, name='dispatch')
class VerifySupervisorDeleteView(LoginRequiredMixin, View):
    """Valida usuario/contraseña de superusuario y habilita una eliminación (marca sesión)."""

    login_url = '/login/'

    def post(self, request):
        username = (request.POST.get('supervisor_username') or '').strip()
        password = request.POST.get('supervisor_password') or ''
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return JsonResponse(
                {'success': False, 'error': 'Usuario o contraseña incorrectos.'},
                status=400,
            )
        if not user.is_superuser:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Solo un superusuario puede autorizar la eliminación.',
                },
                status=403,
            )
        request.session[SUPERVISOR_DELETE_SESSION_KEY] = time.time()
        request.session.modified = True
        return JsonResponse({'success': True})


@method_decorator(require_POST, name='dispatch')
class VerifySupervisorCollectorView(LoginRequiredMixin, View):
    """Valida superusuario para administrar cobradores (Admin Cobranzas)."""

    login_url = '/login/'

    def post(self, request):
        username = (request.POST.get('supervisor_username') or '').strip()
        password = request.POST.get('supervisor_password') or ''
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return JsonResponse(
                {'success': False, 'error': 'Usuario o contraseña incorrectos.'},
                status=400,
            )
        if not user.is_superuser:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Solo un superusuario (Neo) puede autorizar Admin Cobranzas.',
                },
                status=403,
            )
        request.session[SUPERVISOR_COLLECTOR_SESSION_KEY] = time.time()
        request.session.modified = True
        return JsonResponse({'success': True})


@method_decorator(require_POST, name='dispatch')
class VerifySupervisorCollectorSaveView(LoginRequiredMixin, View):
    """Autoriza un registro o edición de cobrador (un uso por guardado)."""

    login_url = '/login/'

    def post(self, request):
        username = (request.POST.get('supervisor_username') or '').strip()
        password = request.POST.get('supervisor_password') or ''
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return JsonResponse(
                {'success': False, 'error': 'Usuario o contraseña incorrectos.'},
                status=400,
            )
        if not user.is_superuser:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Solo un superusuario (Neo) puede autorizar el registro.',
                },
                status=403,
            )
        request.session[SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY] = time.time()
        request.session.modified = True
        return JsonResponse({'success': True})


@method_decorator(require_POST, name='dispatch')
class VerifySupervisorPredioUnlockView(LoginRequiredMixin, View):
    """Valida superusuario para desvincular predios con contrato generado."""

    login_url = '/login/'

    def post(self, request):
        username = (request.POST.get('supervisor_username') or '').strip()
        password = request.POST.get('supervisor_password') or ''
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            return JsonResponse(
                {'success': False, 'error': 'Usuario o contraseña incorrectos.'},
                status=400,
            )
        if not user_can_authorize_predio_unlock(user):
            return JsonResponse(
                {
                    'success': False,
                    'error': (
                        'Solo un usuario supervisor autorizado puede desvincular '
                        'predios con contrato generado.'
                    ),
                },
                status=403,
            )
        request.session[SUPERVISOR_PREDIO_UNLOCK_SESSION_KEY] = time.time()
        request.session.modified = True
        return JsonResponse({'success': True})
