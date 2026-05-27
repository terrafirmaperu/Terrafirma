from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Página pública inicial — sitio nuevo desde cero."""

    template_name = 'website/home.html'
