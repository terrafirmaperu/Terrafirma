import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from core.marketing.advisory_timeline import build_timeline_context, build_timeline_layout
from core.marketing.client_portal import MARKETING_CLIENT_PORTAL_SESSION_KEY, get_portal_client
from core.marketing.contact_email import send_marketing_contact_email
from core.marketing.forms import ClientePortalLoginForm, MarketingContactForm
from core.pos.models import AdvisoryProgressCase, Client


class ClientPortalRequiredMixin:
    """Exige sesión del portal cliente (no el login Factora)."""

    def dispatch(self, request, *args, **kwargs):
        if not get_portal_client(request):
            return redirect('cliente_login')
        return super().dispatch(request, *args, **kwargs)


class MarketingHomeView(TemplateView):
    """Portada / inicio del sistema (web + enlaces a Factora y área cliente)."""

    template_name = 'marketing/inicio.html'


class ClientePortalLoginView(FormView):
    template_name = 'marketing/cliente/login.html'
    form_class = ClientePortalLoginForm

    def dispatch(self, request, *args, **kwargs):
        if get_portal_client(request):
            return redirect('cliente_avances')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        dni = form.cleaned_data['dni'].strip()
        code = form.cleaned_data['client_code'].strip()
        client = (
            Client.objects.select_related('user')
            .filter(
                user__dni__iexact=dni,
                client_code__iexact=code,
            )
            .exclude(client_code__isnull=True)
            .exclude(client_code='')
            .first()
        )
        if not client:
            messages.error(
                self.request,
                'No encontramos un cliente con ese DNI y código. Revise los datos o consulte con la oficina.',
            )
            return self.form_invalid(form)

        self.request.session.cycle_key()
        self.request.session[MARKETING_CLIENT_PORTAL_SESSION_KEY] = client.pk
        messages.success(
            self.request,
            'Bienvenido, {}.'.format(client.user.get_full_name() or client.user.get_username()),
        )
        return HttpResponseRedirect(reverse('cliente_avances'))


class ClientePortalLogoutView(View):
    def get(self, request, *args, **kwargs):
        request.session.pop(MARKETING_CLIENT_PORTAL_SESSION_KEY, None)
        messages.info(request, 'Ha cerrado sesión en el área de cliente.')
        return redirect('home')


class ClientePortalHomeView(ClientPortalRequiredMixin, TemplateView):
    template_name = 'marketing/cliente/avances.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from core.pos.advisory_sale_cases import sync_advisory_cases_for_client

        client = get_portal_client(self.request)
        sync_advisory_cases_for_client(client)
        ctx['page_title'] = 'Mis contratas y avances'
        ctx['portal_client'] = client
        ctx['advisory_cases'] = (
            AdvisoryProgressCase.objects.filter(
                client=client,
                is_visible_portal=True,
            )
            .select_related('sale')
            .prefetch_related('stages', 'sale__saledetail_set__product')
            .order_by('-sale_id', '-updated_at', '-id')
        )
        return ctx


class ClientePortalCaseDetailView(ClientPortalRequiredMixin, TemplateView):
    template_name = 'marketing/cliente/avance_detalle.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from core.pos.advisory_sale_cases import sync_advisory_cases_for_client

        client = get_portal_client(self.request)
        sync_advisory_cases_for_client(client)
        case = get_object_or_404(
            AdvisoryProgressCase.objects.select_related('sale').prefetch_related(
                'stages',
                'sale__saledetail_set__product',
            ),
            pk=self.kwargs['pk'],
            client=client,
            is_visible_portal=True,
        )
        ctx['portal_client'] = client
        ctx['advisory_cases'] = (
            AdvisoryProgressCase.objects.filter(
                client=client,
                is_visible_portal=True,
            )
            .select_related('sale')
            .order_by('-sale_id', '-updated_at', '-id')
        )
        ctx['advisory_case'] = case
        ctx['timeline_stages'] = build_timeline_layout(case)
        ctx['timeline_meta'] = build_timeline_context(case)
        ctx['page_title'] = case.title
        return ctx


class MarketingStubView(TemplateView):
    template_name = 'marketing/stub.html'
    page_title = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = self.page_title
        return ctx


class MarketingQuienesView(MarketingStubView):
    page_title = 'Quiénes somos'


class MarketingServiciosView(MarketingStubView):
    page_title = 'Servicios'


class MarketingAsesoriasView(MarketingStubView):
    page_title = 'Asesorías'


class MarketingContactoView(FormView):
    template_name = 'marketing/contacto.html'
    form_class = MarketingContactForm
    success_url = None

    def get_success_url(self):
        return reverse('marketing_contacto')

    def get_initial(self):
        initial = super().get_initial()
        svc = (self.request.GET.get('servicio') or '').strip()
        valid = {c[0] for c in MarketingContactForm.base_fields['service'].choices if c[0]}
        if svc in valid:
            initial['service'] = svc
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Contacto'
        ctx['page_lead'] = (
            'Cuéntenos sobre su predio o trámite. Le responderemos a '
            '{}.'.format(self._contact_inbox_display())
        )
        return ctx

    @staticmethod
    def _contact_inbox_display():
        from django.conf import settings

        return getattr(settings, 'MARKETING_CONTACT_EMAIL', 'terrafirmaperu@gmail.com')

    def form_valid(self, form):
        try:
            send_marketing_contact_email(form.cleaned_data, request=self.request)
        except Exception as exc:
            logging.getLogger(__name__).exception('Error al enviar contacto web: %s', exc)
            messages.error(
                self.request,
                'No pudimos enviar su mensaje en este momento. '
                'Intente de nuevo o escríbanos directamente a {}.'.format(
                    self._contact_inbox_display(),
                ),
            )
            return self.form_invalid(form)

        messages.success(
            self.request,
            'Su mensaje fue enviado correctamente. Nos comunicaremos con usted a la brevedad.',
        )
        return super().form_valid(form)
