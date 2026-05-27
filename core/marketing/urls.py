"""
Sitio público + portada (misma instancia Django que Factora → un solo runserver).

Rutas (config.urls incluye este módulo en ''):

  /                    Inicio del sistema (portada)
  /quienes-somos/      Información
  /servicios/
  /asesorias/
  /contacto/
  /cliente/ingreso/    Login cliente (DNI + código)
  /cliente/salir/      Cerrar sesión portal cliente
  /cliente/            Área cliente (requiere ingreso)

Factora (mismo proyecto, otras rutas en config.urls):

  /login/              Acceso personal (pantalla dorada)
  /dashboard/          Panel
  /pos/, /reports/, …  Módulos existentes
"""
from django.urls import path

from core.marketing.views import (
    ClientePortalCaseDetailView,
    ClientePortalHomeView,
    ClientePortalLoginView,
    ClientePortalLogoutView,
    MarketingAsesoriasView,
    MarketingContactoView,
    MarketingHomeView,
    MarketingQuienesView,
    MarketingServiciosView,
)

urlpatterns = [
    path('', MarketingHomeView.as_view(), name='home'),
    path('cliente/ingreso/', ClientePortalLoginView.as_view(), name='cliente_login'),
    path('cliente/salir/', ClientePortalLogoutView.as_view(), name='cliente_logout'),
    path('cliente/', ClientePortalHomeView.as_view(), name='cliente_avances'),
    path('cliente/avance/<int:pk>/', ClientePortalCaseDetailView.as_view(), name='cliente_avance_detalle'),
    path('quienes-somos/', MarketingQuienesView.as_view(), name='marketing_quienes'),
    path('servicios/', MarketingServiciosView.as_view(), name='marketing_servicios'),
    path('asesorias/', MarketingAsesoriasView.as_view(), name='marketing_asesorias'),
    path('contacto/', MarketingContactoView.as_view(), name='marketing_contacto'),
]
