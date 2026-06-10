import json

from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from config import settings
from core.security.mixins import ModuleMixin
from core.whatsapp.forms import WhatsAppApiConfigurationForm
from core.whatsapp.models import WhatsAppApiConfiguration
from core.whatsapp.whatsapp_api import test_api_connection


class WhatsAppConfigUpdateView(ModuleMixin, UpdateView):
    template_name = 'whatsapp/config/create.html'
    form_class = WhatsAppApiConfigurationForm
    model = WhatsAppApiConfiguration
    success_url = reverse_lazy('whatsapp_config')

    def get_object(self, queryset=None):
        return WhatsAppApiConfiguration.get_solo()

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'edit':
                instance = self.get_object()
                if instance.pk is not None:
                    form = WhatsAppApiConfigurationForm(request.POST, instance=instance)
                else:
                    form = WhatsAppApiConfigurationForm(request.POST)
                data = form.save()
            elif action == 'test_api':
                test_phone = (request.POST.get('test_phone') or '').strip()
                result = test_api_connection(test_phone=test_phone or None)
                return JsonResponse(result)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        instance = self.get_object()
        context['list_url'] = settings.LOGIN_REDIRECT_URL
        context['title'] = 'Configuración API WhatsApp'
        context['action'] = 'edit'
        context['token_configured'] = instance.token_configured()
        context['messages_endpoint'] = instance.get_messages_endpoint()
        return context
