"""Entregables obrero por producto — uso en ventas y cuentas por cobrar."""

from core.pos.models import Product, ProductWorkerConfig, ProductWorkerDeliverable


def worker_entregables_for_sale(sale):
    """Opciones para combo: inscripción y entregables de cada producto de la venta."""
    if sale is None or not getattr(sale, 'pk', None):
        return []

    product_ids = list(
        sale.saledetail_set.values_list('product_id', flat=True).distinct()
    )
    if not product_ids:
        return []

    options = []
    products = Product.objects.filter(pk__in=product_ids).order_by('name', 'id')
    for product in products:
        try:
            config = product.worker_config
        except ProductWorkerConfig.DoesNotExist:
            config = None

        if config is not None and config.inscription_amount > 0:
            amt = format(config.inscription_amount, '.2f')
            options.append({
                'id': 'inscription-{}'.format(product.id),
                'type': 'inscription',
                'product_id': product.id,
                'product_name': product.name,
                'name': 'Inscripción',
                'charge_amount': amt,
                'label': '{} — Inscripción (S/ {})'.format(product.name, amt),
            })

        deliverables = product.worker_deliverables.order_by('order', 'id')
        for deliverable in deliverables:
            amt = format(deliverable.charge_amount, '.2f')
            options.append({
                'id': 'deliverable-{}'.format(deliverable.id),
                'type': 'deliverable',
                'deliverable_id': deliverable.id,
                'product_id': product.id,
                'product_name': product.name,
                'name': deliverable.name,
                'charge_amount': amt,
                'label': '{} — {} (S/ {})'.format(product.name, deliverable.name, amt),
            })

    return options


def parse_worker_entregable_value(raw):
    """Devuelve (deliverable_id, inscription_product_id) o (None, None)."""
    value = (raw or '').strip()
    if not value:
        return None, None
    if value.startswith('inscription-'):
        try:
            return None, int(value.split('-', 1)[1])
        except (TypeError, ValueError):
            return None, None
    if value.startswith('deliverable-'):
        try:
            return int(value.split('-', 1)[1]), None
        except (TypeError, ValueError):
            return None, None
    return None, None


def resolve_worker_entregable_for_sale(sale, deliverable_id=None, inscription_product_id=None):
    """Valida y devuelve instancias o mensaje de error."""
    product_ids = set(sale.saledetail_set.values_list('product_id', flat=True))

    if deliverable_id:
        deliverable = ProductWorkerDeliverable.objects.select_related('product').filter(
            pk=deliverable_id,
        ).first()
        if not deliverable or deliverable.product_id not in product_ids:
            return None, None, 'El entregable seleccionado no corresponde a esta venta.'
        return deliverable, None, None

    if inscription_product_id:
        if inscription_product_id not in product_ids:
            return None, None, 'La inscripción seleccionada no corresponde a esta venta.'
        product = Product.objects.filter(pk=inscription_product_id).first()
        if not product:
            return None, None, 'Producto de inscripción no encontrado.'
        try:
            config = product.worker_config
        except ProductWorkerConfig.DoesNotExist:
            return None, None, 'El producto no tiene inscripción configurada.'
        if config.inscription_amount <= 0:
            return None, None, 'El producto no tiene monto de inscripción configurado.'
        return None, product, None

    return None, None, None


def worker_credit_reference_for_products(product_ids):
    """
    Referencia de crédito desde configuración Obrero del producto.
    Solo usa el monto de inscripción (si está configurado).
    Toma el primer producto del carrito que tenga alguno de esos datos.
    """
    result = {
        'found': False,
        'has_inscription': False,
        'inscription_amount': '0.00',
        'product_id': None,
        'product_name': '',
    }
    if not product_ids:
        return result

    seen = set()
    ordered_ids = []
    for raw in product_ids:
        try:
            pid = int(raw)
        except (TypeError, ValueError):
            continue
        if pid in seen:
            continue
        seen.add(pid)
        ordered_ids.append(pid)

    for pid in ordered_ids:
        try:
            product = Product.objects.get(pk=pid)
            config = product.worker_config
        except (Product.DoesNotExist, ProductWorkerConfig.DoesNotExist):
            continue

        has_inscription = config.inscription_amount > 0
        if not has_inscription:
            continue

        result['found'] = True
        result['product_id'] = product.id
        result['product_name'] = product.name
        result['has_inscription'] = True
        result['inscription_amount'] = format(config.inscription_amount, '.2f')
        return result

    return result
