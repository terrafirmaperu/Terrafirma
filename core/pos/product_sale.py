from django.conf import settings
from django.db.models import DecimalField, OuterRef, Q, Subquery

from core.pos.models import Product, PromotionsDetail


def active_promo_price_subquery():
    return Subquery(
        PromotionsDetail.objects.filter(
            product_id=OuterRef('pk'),
            promotion__state=True,
        )
        .order_by('id')
        .values('price_final')[:1],
        output_field=DecimalField(max_digits=9, decimal_places=2),
    )


def product_json_for_sale_row(product):
    """Formato de línea de venta (autocomplete / detalle de factura)."""
    raw_promo = getattr(product, '_promo_final', None)
    promo = float(raw_promo) if raw_promo is not None else 0.0
    if promo < 0:
        promo = 0.0
    price_current = promo if promo > 0 else float(product.pvp)
    if product.image:
        image_url = '{}{}'.format(settings.MEDIA_URL, product.image)
    else:
        image_url = '{}{}'.format(settings.STATIC_URL, 'img/default/empty.png')
    return {
        'id': product.id,
        'name': product.name,
        'category': {'id': product.category.id, 'name': product.category.name},
        'price': format(product.price, '.2f'),
        'pvp': format(product.pvp, '.2f'),
        'price_promotion': format(promo, '.2f'),
        'price_current': format(price_current, '.2f'),
        'image': image_url,
        'value': product.name,
        'dscto': '0.00',
        'total_dscto': '0.00',
    }


def products_catalog_for_predio():
    """Opciones para el selector de producto en cada predio del cliente."""
    return [
        {
            'id': p.id,
            'name': p.name,
            'category': p.category.name if p.category_id else '',
            'price_current': format(p.get_price_current(), '.2f'),
        }
        for p in Product.objects.select_related('category').order_by('name')
    ]


def search_products_for_predio(term='', exclude_ids=None, limit=25):
    exclude_ids = exclude_ids or []
    qs = (
        Product.objects.exclude(id__in=exclude_ids)
        .select_related('category')
        .annotate(_promo_final=active_promo_price_subquery())
    )
    term = (term or '').strip()
    if term:
        qs = qs.filter(
            Q(name__icontains=term) | Q(category__name__icontains=term)
        ).order_by('name')
    else:
        qs = qs.order_by('name')
    return [product_json_for_sale_row(p) for p in qs[:limit]]
