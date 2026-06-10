from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy

from core.pos.models import CashRegisterSession


class CashRegisterRequiredMixin(object):
    cash_required_message = (
        'No hay caja abierta en el sistema. El responsable del turno debe realizar la apertura.'
    )

    @staticmethod
    def _post_expects_json(request):
        """Evita 302 HTML en XHR (DataTables/jQuery): eso dispara Ajax error tn/7."""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        accept = request.headers.get('Accept') or ''
        return 'application/json' in accept

    def has_open_cash(self, request):
        return CashRegisterSession.get_open_session() is not None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.method == 'POST' and self._post_expects_json(request):
                return JsonResponse({
                    'error': 'Debe iniciar sesión para realizar esta acción.',
                    'not_authenticated': True,
                }, status=200)
            return redirect_to_login(request.get_full_path())
        if not self.has_open_cash(request):
            if request.method == 'POST':
                return JsonResponse({
                    'error': self.cash_required_message,
                    'cash_required': True,
                }, status=200)
            messages.warning(request, self.cash_required_message)
            return HttpResponseRedirect(reverse_lazy('cashsession_list'))
        return super().dispatch(request, *args, **kwargs)
