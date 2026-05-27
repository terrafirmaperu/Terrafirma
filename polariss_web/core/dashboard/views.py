from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    """Panel interno tras login — mismo rol conceptual que Factora (vtcpanel / métricas)."""

    template_name = 'dashboard/panel.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            request.user.set_group_session()
        return super().get(request, *args, **kwargs)
