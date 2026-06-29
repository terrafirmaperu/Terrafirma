import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import FormView, RedirectView, TemplateView

from config import settings
from core.login.forms import CaseInsensitiveAuthenticationForm, ResetPasswordForm, ChangePasswordForm
from core.security.models import AccessUsers
from core.security.role_groups import repair_supervisor_module_links
from core.user.models import User


class LoginAuthView(LoginView):
    form_class = CaseInsensitiveAuthenticationForm
    template_name = 'login/login_golden.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault('title', 'Inicio de Sesión — Factora')
        login_errors = self.request.session.pop('login_errors', None)
        if login_errors:
            ctx['login_errors'] = login_errors
        return ctx

    def get_form(self, form_class=None):
        form = super(LoginAuthView, self).get_form()
        form.fields['username'].widget.attrs = {
            'class': 'form-control',
            'placeholder': 'Ingrese su username',
            'autocomplete': 'off',
            'autofocus': True,
        }
        form.fields['password'].widget.attrs = {
            'class': 'form-control',
            'placeholder': 'Ingrese su password',
            'autocomplete': 'off',
        }
        return form

    def get(self, request, *args, **kwargs):
        login_different = reverse_lazy('login_different')
        if request.user.is_authenticated and login_different != request.path:
            return HttpResponseRedirect(reverse_lazy('login_authenticated'))
        return super().get(request, *args, **kwargs)

    def form_invalid(self, form):
        errors = []
        for field in form:
            for error in field.errors:
                errors.append(str(error))
        for error in form.non_field_errors():
            errors.append(str(error))
        if not errors:
            errors.append('Usuario o contraseña incorrectos.')
        self.request.session['login_errors'] = errors
        return HttpResponseRedirect(reverse_lazy('login'))

    def form_valid(self, form):
        login(self.request, form.get_user())
        if self.request.user.is_authenticated:
            repair_supervisor_module_links(self.request.user)
            self.request.user.set_group_session()
            AccessUsers(user=self.request.user).save()
        return HttpResponseRedirect(self.get_success_url())


class LoginAuthenticatedView(TemplateView):
    template_name = 'login/login_authenticated.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sesión activa — Qori'
        return context


class ResetPasswordView(FormView):
    template_name = 'login/reset_pwd.html'
    form_class = ResetPasswordForm
    success_url = settings.LOGIN_URL

    def send_email_reset_pwd(self, user):
        with transaction.atomic():
            url = settings.LOCALHOST if not settings.DEBUG else self.request.META['HTTP_HOST']
            user.is_change_password = True
            user.save()

            activate_account = '{}{}{}{}'.format('http://', url, '/login/change/password/', user.token)
            message = MIMEMultipart('alternative')
            message['Subject'] = 'Reseteo de contraseña'
            message['From'] = settings.EMAIL_HOST_USER
            message['To'] = user.email

            parameters = {
                'user': user,
                'link_resetpwd': activate_account,
                'link_home': 'http://{}'.format(url)
            }

            html = render_to_string('login/send_email.html', parameters)
            content = MIMEText(html, 'html')
            message.attach(content)
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(
                settings.EMAIL_HOST_USER, user.email, message.as_string()
            )
            server.quit()

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            form = self.get_form()
            if form.is_valid():
                self.send_email_reset_pwd(form.get_user())
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reseteo de contraseña'
        return context


class ChangePasswordView(FormView):
    template_name = 'login/change_pwd.html'
    form_class = ChangePasswordForm
    success_url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        token = kwargs['pk']
        if User.objects.filter(token=token, is_change_password=True).exists():
            return super().get(request, *args, **kwargs)
        return HttpResponseRedirect(self.success_url)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            form = self.get_form()
            if form.is_valid():
                user = User.objects.get(token=kwargs['pk'])
                user.is_change_password = False
                user.set_password(request.POST['password'])
                user.save()
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cambio de contraseña'
        return context


class LogoutRedirectView(RedirectView):
    pattern_name = 'login'

    def dispatch(self, request, *args, **kwargs):
        logout(request)
        return super().dispatch(request, *args, **kwargs)
