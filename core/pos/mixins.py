from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy

from core.pos.models import CashRegisterSession


class CashRegisterRequiredMixin(object):
    cash_required_message = 'Debe tener una caja abierta para acceder a este módulo'

    @staticmethod
    def _post_expects_json(request):
        """Evita 302 HTML en XHR (DataTables/jQuery): eso dispara Ajax error tn/7."""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        accept = request.headers.get('Accept') or ''
        return 'application/json' in accept

    def has_open_cash(self, request):
        return CashRegisterSession.objects.filter(
            user_opened=request.user,
            status=CashRegisterSession.OPEN
        ).exists()

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
                # HTTP 200: DataTables/jQuery.ajax tratan 4xx como fallo de Ajax (tn/7) y no parsean el JSON.
                return JsonResponse({
                    'error': self.cash_required_message,
                    'cash_required': True,
                }, status=200)
            messages.warning(request, self.cash_required_message)
            return HttpResponseRedirect(reverse_lazy('cashsession_create'))
        return super().dispatch(request, *args, **kwargs)
