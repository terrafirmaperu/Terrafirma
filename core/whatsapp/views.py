from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import RedirectView

WHATSAPP_WEB_URL = 'https://web.whatsapp.com'


class WhatsAppWebView(LoginRequiredMixin, RedirectView):
    permanent = False
    url = WHATSAPP_WEB_URL
