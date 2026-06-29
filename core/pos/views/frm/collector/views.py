import json

from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.pos.forms import CollectorForm
from core.pos.models import Collector
from core.security.mixins import (
    PermissionMixin,
    SupervisorCollectorMixin,
    SupervisorDeleteApprovalMixin,
    require_supervisor_collector_save,
)


class CollectorListView(SupervisorCollectorMixin, PermissionMixin, ListView):
    model = Collector
    template_name = 'frm/collector/list.html'
    permission_required = 'view_collector'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('collector_create')
        context['title'] = 'Listado de Cobradores'
        return context


class CollectorCreateView(SupervisorCollectorMixin, PermissionMixin, CreateView):
    model = Collector
    template_name = 'frm/collector/create.html'
    form_class = CollectorForm
    success_url = reverse_lazy('collector_list')
    permission_required = 'add_collector'

    def validate_data(self):
        data = {'valid': True}
        try:
            obj = self.request.POST['obj'].strip()
            if Collector.objects.filter(name__iexact=obj):
                data['valid'] = False
        except Exception:
            pass
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'add':
            blocked = require_supervisor_collector_save(request)
            if blocked:
                return blocked
        data = {}
        try:
            if action == 'add':
                data = self.get_form().save()
                from core.security.mixins import SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY
                from core.security.supervisor_audit import log_supervisor_event, pop_supervisor_authorizer
                supervisor = pop_supervisor_authorizer(request, SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY)
                name = (request.POST.get('name') or '').strip()
                log_supervisor_event(
                    request,
                    'action_collector_save',
                    category='accion',
                    detail='Registro nuevo en Admin Cobranzas.',
                    change_summary='Alta de cobrador: «{}»'.format(name or '—'),
                    supervisor_user=supervisor,
                    object_type='Collector',
                )
            elif action == 'validate_data':
                return self.validate_data()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo cobrador'
        context['action'] = 'add'
        context['collector_user_is_superuser'] = self.request.user.is_superuser
        return context


class CollectorUpdateView(SupervisorCollectorMixin, PermissionMixin, UpdateView):
    model = Collector
    template_name = 'frm/collector/create.html'
    form_class = CollectorForm
    success_url = reverse_lazy('collector_list')
    permission_required = 'change_collector'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def validate_data(self):
        data = {'valid': True}
        try:
            obj = self.request.POST['obj'].strip()
            if Collector.objects.filter(name__iexact=obj).exclude(pk=self.get_object().pk):
                data['valid'] = False
        except Exception:
            pass
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'edit':
            blocked = require_supervisor_collector_save(request)
            if blocked:
                return blocked
        data = {}
        try:
            if action == 'edit':
                data = self.get_form().save()
                from core.security.mixins import SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY
                from core.security.supervisor_audit import log_supervisor_event, pop_supervisor_authorizer
                supervisor = pop_supervisor_authorizer(request, SUPERVISOR_COLLECTOR_SAVE_SESSION_KEY)
                old_name = self.object.name
                new_name = (request.POST.get('name') or self.object.name or '').strip()
                log_supervisor_event(
                    request,
                    'action_collector_save',
                    category='accion',
                    detail='Edición en Admin Cobranzas (id {}).'.format(self.object.pk),
                    change_summary='Cobrador renombrado: «{}» → «{}»'.format(old_name, new_name),
                    supervisor_user=supervisor,
                    object_type='Collector',
                    object_id=self.object.pk,
                )
            elif action == 'validate_data':
                return self.validate_data()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Edición de cobrador'
        context['action'] = 'edit'
        context['collector_user_is_superuser'] = self.request.user.is_superuser
        return context


class CollectorDeleteView(SupervisorCollectorMixin, SupervisorDeleteApprovalMixin, PermissionMixin, DeleteView):
    model = Collector
    template_name = 'frm/collector/delete.html'
    success_url = reverse_lazy('collector_list')
    permission_required = 'delete_collector'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notificación de eliminación'
        context['list_url'] = self.success_url
        return context
