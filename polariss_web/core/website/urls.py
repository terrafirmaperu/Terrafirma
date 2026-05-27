from django.urls import path

from core.website.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home_public'),
]
