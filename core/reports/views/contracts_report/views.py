# -*- coding: utf-8 -*-
import json

from django.http import HttpResponse
from django.views.generic import TemplateView

from core.reports.contracts_report import (
    get_contracts_report_filter_options,
    search_contracts_report,
)
from core.security.mixins import ModuleMixin


class ContractsReportView(ModuleMixin, TemplateView):
    template_name = 'contracts_report/report.html'

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        data = {}
        try:
            if action == 'filter_options':
                data = get_contracts_report_filter_options()
            elif action == 'search_report':
                filters = {
                    'product': request.POST.get('product', ''),
                    'department': request.POST.get('department', ''),
                    'province': request.POST.get('province', ''),
                    'district': request.POST.get('district', ''),
                    'community': request.POST.get('community', ''),
                    'population_center': request.POST.get('population_center', ''),
                    'predio_type': request.POST.get('predio_type', ''),
                    'location_type': request.POST.get('location_type', ''),
                    'location_filters_enabled': request.POST.get('location_filters_enabled', '0'),
                }
                data = search_contracts_report(filters)
            else:
                data = {'error': 'Acción no válida'}
        except Exception as exc:
            data = {'error': str(exc)}
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Contratos'
        return context
