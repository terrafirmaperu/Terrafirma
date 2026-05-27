# -*- coding: utf-8 -*-
import json

from django.http import HttpResponse
from django.views.generic import TemplateView

from core.reports.client_report import (
    get_client_report_filter_options,
    search_clients_report,
)
from core.security.mixins import ModuleMixin


class ClientReportView(ModuleMixin, TemplateView):
    template_name = 'client_report/report.html'

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        data = {}
        try:
            if action == 'filter_options':
                data = get_client_report_filter_options()
            elif action == 'search_report':
                data = search_clients_report({
                    'location_type': request.POST.get('location_type', ''),
                    'community': request.POST.get('community', ''),
                    'population_center': request.POST.get('population_center', ''),
                    'province': request.POST.get('province', ''),
                    'district': request.POST.get('district', ''),
                })
            else:
                data = {'error': 'Acción no válida'}
        except Exception as e:
            data = {'error': str(e)}
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Clientes'
        return context
