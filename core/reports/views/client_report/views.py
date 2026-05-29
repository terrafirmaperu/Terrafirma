# -*- coding: utf-8 -*-
import json

from django.http import HttpResponse
from django.views.generic import TemplateView

from core.reports.client_report import (
    cancellations_report,
    debtors_report,
    enrollment_summary_report,
    get_client_report_filter_options,
    paid_today_report,
    payments_by_day_report,
    product_enrollment_debt_report,
    product_quota_payments_report,
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
                filters = {
                    'location_type': request.POST.get('location_type', ''),
                    'community': request.POST.get('community', ''),
                    'population_center': request.POST.get('population_center', ''),
                    'province': request.POST.get('province', ''),
                    'district': request.POST.get('district', ''),
                }
                data = search_clients_report(filters)
            elif action == 'enrollment_summary_report':
                data = enrollment_summary_report({
                    'location_type': request.POST.get('location_type', ''),
                    'community': request.POST.get('community', ''),
                    'population_center': request.POST.get('population_center', ''),
                    'province': request.POST.get('province', ''),
                    'district': request.POST.get('district', ''),
                })
            elif action == 'product_enrollment_debt_report':
                data = product_enrollment_debt_report({
                    'location_type': request.POST.get('location_type', ''),
                    'community': request.POST.get('community', ''),
                    'population_center': request.POST.get('population_center', ''),
                    'province': request.POST.get('province', ''),
                    'district': request.POST.get('district', ''),
                })
            elif action == 'product_quota_payments_report':
                data = product_quota_payments_report({
                    'location_type': request.POST.get('location_type', ''),
                    'community': request.POST.get('community', ''),
                    'population_center': request.POST.get('population_center', ''),
                    'province': request.POST.get('province', ''),
                    'district': request.POST.get('district', ''),
                    'product': request.POST.get('product', ''),
                })
            elif action == 'paid_today_report':
                data = paid_today_report(request.user)
            elif action == 'debtors_report':
                data = debtors_report(request.POST.get('term', ''))
            elif action == 'payments_by_day_report':
                data = payments_by_day_report(
                    request.POST.get('start_date', ''),
                    request.POST.get('end_date', ''),
                )
            elif action == 'cancellations_report':
                data = cancellations_report(
                    request.POST.get('start_date', ''),
                    request.POST.get('end_date', ''),
                )
            else:
                data = {'error': 'Acción no válida'}
        except Exception as e:
            data = {'error': str(e)}
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Clientes'
        return context
