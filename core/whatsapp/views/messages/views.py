import json

from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, TemplateView

from core.whatsapp.whatsapp_recipients import get_whatsapp_filter_options
from core.security.mixins import ModuleMixin, PermissionMixin, SupervisorDeleteApprovalMixin
from core.whatsapp.forms import WhatsAppBulkMessageForm
from core.whatsapp.models import WhatsAppBulkMessage
from core.whatsapp.whatsapp_api import send_bulk_message
from core.whatsapp.whatsapp_recipients import (
    AUDIENCE_CHOICES,
    LOCATION_BASE_CHOICES,
    count_phones_for_post,
)


class WhatsAppMessageListView(ModuleMixin, TemplateView):
    template_name = 'whatsapp/messages/list.html'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'search':
                rows = [row.toJSON() for row in WhatsAppBulkMessage.objects.all()]
                return HttpResponse(json.dumps(rows), content_type='application/json')
            if action == 'preview_count':
                return JsonResponse({'count': count_phones_for_post(request.POST)})
            data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mensajes masivos WhatsApp'
        context['create_url'] = reverse_lazy('whatsapp_messages_create')
        return context


class WhatsAppMessageCreateView(PermissionMixin, CreateView):
    template_name = 'whatsapp/messages/create.html'
    form_class = WhatsAppBulkMessageForm
    model = WhatsAppBulkMessage
    success_url = reverse_lazy('whatsapp_messages')
    permission_required = 'add_whatsappbulkmessage'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'preview_count':
                return JsonResponse({'count': count_phones_for_post(request.POST)})
            if action == 'filter_options':
                return JsonResponse(get_whatsapp_filter_options())
            if action == 'add':
                form = WhatsAppBulkMessageForm(request.POST, filter_post=request.POST)
                data = form.save(user=request.user)
                if not data.get('error') and form.instance.pk:
                    if request.POST.get('send_now') == '1':
                        send_bulk_message(form.instance)
            elif action == 'send_existing':
                pk = request.POST.get('id')
                campaign = WhatsAppBulkMessage.objects.filter(pk=pk).first()
                if not campaign:
                    data['error'] = 'Campaña no encontrada'
                else:
                    send_bulk_message(campaign)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo mensaje masivo'
        context['action'] = 'add'
        context['filter_options'] = get_whatsapp_filter_options()
        context['audience_choices'] = AUDIENCE_CHOICES
        context['location_base_choices'] = LOCATION_BASE_CHOICES
        return context


class WhatsAppMessageDeleteView(SupervisorDeleteApprovalMixin, PermissionMixin, DeleteView):
    model = WhatsAppBulkMessage
    template_name = 'whatsapp/messages/delete.html'
    success_url = reverse_lazy('whatsapp_messages')
    permission_required = 'delete_whatsappbulkmessage'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'delete':
                self.object = self.get_object()
                self.object.delete()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Eliminar mensaje masivo'
        return context
