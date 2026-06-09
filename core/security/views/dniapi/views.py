import json

from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from config import settings
from core.pos.dni_lookup import lookup_dni_data
from core.security.forms import DniApiConfiguration, DniApiConfigurationForm
from core.security.mixins import ModuleMixin


class DniApiConfigurationUpdateView(ModuleMixin, UpdateView):
    template_name = 'dniapi/create.html'
    form_class = DniApiConfigurationForm
    model = DniApiConfiguration
    success_url = reverse_lazy('dniapi_update')

    def get_object(self, queryset=None):
        return DniApiConfiguration.get_solo()

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'edit':
                instance = self.get_object()
                if instance.pk is not None:
                    form = DniApiConfigurationForm(request.POST, instance=instance)
                else:
                    form = DniApiConfigurationForm(request.POST)
                data = form.save()
            elif action == 'test_dni':
                dni = (request.POST.get('test_dni') or '').strip()
                payload = lookup_dni_data(dni)
                if payload.get('error'):
                    return JsonResponse({
                        'success': False,
                        'error': payload['error'],
                        'skipped': bool(payload.get('skipped')),
                    })
                return JsonResponse({'success': True, 'data': payload})
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        instance = self.get_object()
        context['list_url'] = settings.LOGIN_REDIRECT_URL
        context['title'] = 'Configuración API DNI (RENIEC)'
        context['action'] = 'edit'
        context['token_configured'] = instance.token_configured()
        return context
