from django.urls import path
from django.views.generic import RedirectView

from core.whatsapp.views.config.views import WhatsAppConfigUpdateView
from core.whatsapp.views.messages.views import (
    WhatsAppMessageCreateView,
    WhatsAppMessageDeleteView,
    WhatsAppMessageListView,
)

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='whatsapp_messages', permanent=False)),
    path('config/', WhatsAppConfigUpdateView.as_view(), name='whatsapp_config'),
    path('messages/', WhatsAppMessageListView.as_view(), name='whatsapp_messages'),
    path('messages/add/', WhatsAppMessageCreateView.as_view(), name='whatsapp_messages_create'),
    path('messages/delete/<int:pk>/', WhatsAppMessageDeleteView.as_view(), name='whatsapp_messages_delete'),
]
