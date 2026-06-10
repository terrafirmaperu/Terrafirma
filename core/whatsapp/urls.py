from django.urls import path

from core.whatsapp.views import WhatsAppWebView

urlpatterns = [
    path('', WhatsAppWebView.as_view(), name='whatsapp'),
]
