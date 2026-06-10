"""URL principal — un solo runserver.

Portada y web informativa: path('', include('core.marketing.urls')).
Factora: /login/, /dashboard/, /pos/, /reports/, etc.

Ver también core/marketing/urls.py.
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config import settings
from core.dashboard.views import *

urlpatterns = [
    path('', include('core.marketing.urls')),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin/', admin.site.urls),
    path('security/', include('core.security.urls')),
    path('login/', include('core.login.urls')),
    path('user/', include('core.user.urls')),
    path('pos/', include('core.pos.urls')),
    path('reports/', include('core.reports.urls')),
    path('whatsapp/', include('core.whatsapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
