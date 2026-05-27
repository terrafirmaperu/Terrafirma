import json

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from core.pos.forms import CompanyForm, Company
from core.security.mixins import ModuleMixin


class CompanyUpdateView(ModuleMixin, UpdateView):
    template_name = 'crm/company/create.html'
    form_class = CompanyForm
    model = Company
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        company = Company.objects.all()
        if company.exists():
            return company[0]
        return Company()

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            instance = self.get_object()
            if instance.pk is not None:
                form = CompanyForm(request.POST, request.FILES, instance=instance)
            else:
                form = CompanyForm(request.POST, request.FILES)
            data = form.save()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = 'Configuración de la Compañia'
        context['list_url'] = self.success_url
        return context
