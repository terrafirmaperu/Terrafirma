from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, FloatField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token
from django.views.generic import TemplateView

from core.pos.models import Product, Sale, Client, Category, Purchase, Company
from core.reports.choices import months
from core.security.models import Dashboard
from core.security.role_groups import panel_module_types_for_group, repair_supervisor_module_links
from core.security.session_group import get_group_from_session


class DashboardView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        dashboard = Dashboard.objects.filter()
        if dashboard.exists():
            if dashboard[0].layout == 1:
                return 'vtcpanel.html'
        return 'hztpanel.html'

    def get(self, request, *args, **kwargs):
        repair_supervisor_module_links(request.user)
        request.user.set_group_session()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'get_graph_stock_products':
                info = []
                for i in Product.objects.all().order_by('-pvp')[0:10]:
                    info.append([i.name, float(i.pvp)])
                data = {
                    'name': 'Productos por Precio',
                    'type': 'pie',
                    'colorByPoint': True,
                    'data': info,
                }
            elif action == 'get_graph_purchase_vs_sale':
                data = []
                year = datetime.now().year
                rows = []
                for i in months[1:]:
                    result = Sale.objects.filter(date_joined__month=i[0], date_joined__year=year).aggregate(
                        resp=Coalesce(Sum('total'), 0.00, output_field=FloatField()))['resp']
                    rows.append(float(result))
                data.append({'name': 'Ventas', 'data': rows})
                rows = []
                for i in months[1:]:
                    result = Purchase.objects.filter(date_joined__month=i[0], date_joined__year=year).aggregate(
                        resp=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['resp']
                    rows.append(float(result))
                data.append({'name': 'Compras', 'data': rows})
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Panel de administración'
        context['company'] = Company.objects.first()
        context['clients'] = Client.objects.all().count()
        context['category'] = Category.objects.filter().count()
        context['product'] = Product.objects.all().count()
        context['sale'] = Sale.objects.filter().order_by('-id')[0:10]
        group = get_group_from_session(self.request)
        context['panel_module_types'] = panel_module_types_for_group(group)
        return context


@requires_csrf_token
def error_404(request, exception):
    return render(request, '404.html', {})


@requires_csrf_token
def error_500(request, exception):
    return render(request, '500.html', {})
