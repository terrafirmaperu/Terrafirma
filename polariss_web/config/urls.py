from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config import settings
from core.dashboard.views import DashboardView
from core.website.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin/', admin.site.urls),
    path('security/', include('core.security.urls')),
    path('login/', include('core.login.urls')),
    path('user/', include('core.user.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
