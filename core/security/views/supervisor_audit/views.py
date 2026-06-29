# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import ListView

from config import settings
from core.security.models import SupervisorAuditLog
from core.security.supervisor_audit import is_neo_user


class NeoRegistrosListView(LoginRequiredMixin, ListView):
    """Solo usuario Neo: historial de autorizaciones y acciones sensibles."""

    model = SupervisorAuditLog
    template_name = 'security/supervisor_audit/list.html'
    context_object_name = 'logs'
    paginate_by = 50
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not is_neo_user(request.user):
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            SupervisorAuditLog.objects.select_related('actor_user', 'supervisor_user')
            .order_by('-created_at', '-id')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Registros de cambios (supervisor)'
        ctx['list_url'] = reverse_lazy('supervisor_audit_list')
        return ctx
