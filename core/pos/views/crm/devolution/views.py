import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, FormView

from core.pos.forms import *
from core.reports.forms import ReportForm
from core.security.mixins import PermissionMixin, SupervisorDeleteApprovalMixin


class DevolutionListView(PermissionMixin, FormView):
    template_name = 'crm/devolution/list.html'
    permission_required = 'view_devolution'
    form_class = ReportForm

    def get_form(self, form_class=None):
        form = ReportForm()
        query = Sale.objects.filter(id__in=Devolution.objects.filter().order_by('saledetail__sale').values_list('saledetail__sale_id', flat=True).distinct())
        choices = [('', '-------')]
        for s in query:
            choices.append((s.id, s.__str__()))
        form.fields['sale'].choices = choices
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                search = Devolution.objects.filter()
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                sale = request.POST['sale']
                if len(start_date) and len(end_date):
                    search = search.filter(date_joined__range=[start_date, end_date])
                if len(sale):
                    search = search.filter(saledetail__sale_id=sale)
                for a in search:
                    item = a.toJSON()
                    item['saledetail']['sale'] = a.saledetail.sale.toJSON()
                    data.append(item)
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Devoluciones'
        context['create_url'] = reverse_lazy('devolution_create')
        return context


class DevolutionCreateView(PermissionMixin, CreateView):
    model = Devolution
    template_name = 'crm/devolution/create.html'
    form_class = DevolutionForm
    success_url = reverse_lazy('devolution_list')
    permission_required = 'add_devolution'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search_sale':
                data = []
                term = request.POST['term']
                for i in Sale.objects.filter(Q(client__user__first_name__icontains=term) | Q(client__user__last_name__icontains=term) | Q(client__user__dni__icontains=term))[0:10]:
                    item = i.toJSON()
                    item['text'] = i.__str__()
                    data.append(item)
            elif action == 'search_products_detail':
                data = []
                for d in SaleDetail.objects.filter(sale_id=request.POST['id']):
                    item = d.toJSON()
                    item['amount_return'] = 0
                    item['state'] = 0
                    item['motive'] = ''
                    data.append(item)
            elif action == 'add':
                with transaction.atomic():
                    products = json.loads(request.POST['products'])
                    for p in products:
                        devolution = Devolution()
                        devolution.saledetail_id = int(p['id'])
                        devolution.cant = int(p['amount_return'])
                        devolution.motive = p['motive']
                        devolution.save()
                        devolution.saledetail.cant -= devolution.cant
                        devolution.saledetail.save()
                        devolution.saledetail.sale.calculate_invoice()
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Devolución'
        context['action'] = 'add'
        return context


class DevolutionDeleteView(SupervisorDeleteApprovalMixin, PermissionMixin, DeleteView):
    model = Devolution
    template_name = 'crm/devolution/delete.html'
    success_url = reverse_lazy('devolution_list')
    permission_required = 'delete_devolution'

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
