import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from core.pos.models import (
    ADVISORY_DEFAULT_STAGE_TITLES,
    Product,
    ProductWorkerConfig,
    ProductWorkerDeliverable,
)
from core.security.mixins import PermissionMixin


def _parse_decimal(value, default='0.00'):
    try:
        return Decimal(str(value).replace(',', '.').strip() or default)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)



@method_decorator(ensure_csrf_cookie, name='dispatch')
class ProductWorkerConfigView(PermissionMixin, TemplateView):
    """Cuotas y entregables del obrero vinculados al producto."""

    template_name = 'scm/product/worker.html'
    permission_required = 'change_product'

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product.objects.select_related('category'), pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        try:
            if action == 'load':
                return self._load_config()
            if action == 'save':
                return self._save_config(request)
            return JsonResponse({'error': 'Acción no válida'})
        except Exception as exc:
            return JsonResponse({'error': str(exc)})

    def _load_config(self):
        config, _ = ProductWorkerConfig.objects.get_or_create(product=self.product)
        deliverables = [
            d.toJSON()
            for d in self.product.worker_deliverables.order_by('order', 'id')
        ]
        return JsonResponse({
            'product': {
                'id': self.product.id,
                'name': self.product.name,
                'category': self.product.category.name,
                'pvp': format(self.product.pvp, '.2f'),
            },
            'config': config.toJSON(),
            'deliverables': deliverables,
            'suggested_stages': list(ADVISORY_DEFAULT_STAGE_TITLES),
        })

    def _save_config(self, request):
        inscription_amount = _parse_decimal(request.POST.get('inscription_amount'))

        raw = request.POST.get('deliverables', '[]')
        try:
            rows = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Formato de entregables inválido.'})
        if not isinstance(rows, list):
            return JsonResponse({'error': 'Formato de entregables inválido.'})

        cleaned = []
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            name = (row.get('name') or '').strip()
            if not name:
                continue
            cleaned.append({
                'id': row.get('id'),
                'order': idx + 1,
                'name': name[:200],
                'charge_amount': _parse_decimal(row.get('charge_amount')),
                'notes': (row.get('notes') or '').strip()[:300],
            })

        with transaction.atomic():
            config, _ = ProductWorkerConfig.objects.get_or_create(product=self.product)
            config.quota_count = 1
            config.inscription_amount = inscription_amount
            config.quotas_enabled = False
            config.save()

            kept_ids = []
            for row in cleaned:
                obj = None
                row_id = row.get('id')
                if row_id:
                    obj = ProductWorkerDeliverable.objects.filter(
                        pk=row_id,
                        product=self.product,
                    ).first()
                if obj is None:
                    obj = ProductWorkerDeliverable(product=self.product)
                obj.order = row['order']
                obj.name = row['name']
                obj.charge_amount = row['charge_amount']
                obj.notes = row['notes']
                obj.save()
                kept_ids.append(obj.id)

            ProductWorkerDeliverable.objects.filter(product=self.product).exclude(
                pk__in=kept_ids,
            ).delete()

            worker_total = inscription_amount + sum(
                row['charge_amount'] for row in cleaned
            )
            config.quota_amount = worker_total.quantize(Decimal('0.01'))
            config.save(update_fields=['quota_amount'])

        config.refresh_from_db()
        deliverables = [
            d.toJSON()
            for d in self.product.worker_deliverables.order_by('order', 'id')
        ]
        return JsonResponse({
            'message': 'Configuración de obrero guardada correctamente.',
            'config': config.toJSON(),
            'deliverables': deliverables,
        })

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Obrero — {}'.format(self.product.name)
        ctx['product'] = self.product
        ctx['list_url'] = reverse_lazy('product_list')
        ctx['worker_url'] = reverse('product_worker', kwargs={'pk': self.product.pk})
        return ctx
