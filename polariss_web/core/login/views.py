import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import FormView, RedirectView, TemplateView

from config import settings
from core.login.forms import ChangePasswordForm, ResetPasswordForm
from core.user.models import User


class LoginAuthView(LoginView):
    form_class = AuthenticationForm
    template_name = 'login/login.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'].widget.attrs.update(
            {
                'class': 'form-control',
                'placeholder': 'Usuario',
                'autocomplete': 'off',
                'autofocus': True,
            }
        )
        form.fields['password'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Contraseña', 'autocomplete': 'off'}
        )
        return form

    def form_valid(self, form):
        login(self.request, form.get_user())
        if self.request.user.is_authenticated:
            self.request.user.set_group_session()
        return HttpResponseRedirect(self.get_success_url())


class LoginAuthenticatedView(TemplateView):
    template_name = 'login/login_authenticated.html'


class ResetPasswordView(FormView):
    template_name = 'login/reset_pwd.html'
    form_class = ResetPasswordForm
    success_url = settings.LOGIN_URL

    def send_email_reset_pwd(self, user):
        if not settings.EMAIL_HOST_PASSWORD:
            raise RuntimeError('Configure EMAIL_HOST_PASSWORD para envío SMTP.')
        with transaction.atomic():
            url = settings.LOCALHOST if not settings.DEBUG else self.request.META.get('HTTP_HOST', settings.LOCALHOST)
            user.is_change_password = True
            user.save()

            activate_account = 'http://{}/login/change/password/{}/'.format(url, user.token)
            message = MIMEMultipart('alternative')
            message['Subject'] = 'Reseteo de contraseña'
            message['From'] = settings.EMAIL_HOST_USER
            message['To'] = user.email

            parameters = {
                'user': user,
                'link_resetpwd': activate_account,
                'link_home': 'http://{}'.format(url),
            }

            html = render_to_string('login/send_email.html', parameters)
            content = MIMEText(html, 'html')
            message.attach(content)
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, user.email, message.as_string())
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
