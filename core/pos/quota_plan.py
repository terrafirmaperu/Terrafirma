"""Validación y aplicación de planes de cuotas personalizados (cuentas por cobrar)."""
import json
from decimal import Decimal

from django.utils.dateparse import parse_date


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def normalize_quota_plan_item(raw, fallback_num=None):
    num = raw.get('num', fallback_num)
    if num is None:
        raise ValueError('Cada cuota debe tener un número de referencia.')
    try:
        num = int(num)
    except (TypeError, ValueError):
        raise ValueError('Número de cuota inválido.')
    amount = _money(raw.get('amount'))
    if amount < 0:
        raise ValueError('El monto de la cuota no puede ser negativo.')
    due_raw = (raw.get('due_date') or '').strip()
    due = parse_date(due_raw)
    if not due:
        raise ValueError('Fecha de cuota inválida: {}'.format(due_raw or '—'))
    label = (raw.get('label') or '').strip()
    if not label:
        if num == 0:
            label = 'Inicial'
        else:
            label = 'Cuota {}'.format(num)
    return {
        'num': num,
        'label': label,
        'amount': format(amount, '.2f'),
        'due_date': due.strftime('%Y-%m-%d'),
    }


def parse_quota_plan_payload(raw_json, sale_total):
    try:
        payload = json.loads(raw_json or '[]')
    except json.JSONDecodeError:
        raise ValueError('Formato de cuotas inválido.')
    if not isinstance(payload, list) or not payload:
        raise ValueError('Debe indicar al menos una cuota.')
    plan = []
    nums = set()
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError('Formato de cuota inválido.')
        row = normalize_quota_plan_item(item, fallback_num=idx)
        if row['num'] in nums:
            raise ValueError('Hay cuotas con el mismo número de referencia.')
        nums.add(row['num'])
        plan.append(row)
    plan.sort(key=lambda x: x['num'])
    total_sale = _money(sale_total)
    plan_total = sum(_money(row['amount']) for row in plan)
    if abs(plan_total - total_sale) > Decimal('0.02'):
        raise ValueError(
            'La suma de cuotas (S/ {}) debe coincidir con el total de la venta (S/ {}).'.format(
                format(plan_total, '.2f'),
                format(total_sale, '.2f'),
            )
        )
    regular = [row for row in plan if row['num'] > 0]
    if not regular:
        raise ValueError('Debe existir al menos una cuota programada (además de la inicial, si aplica).')
    if len(regular) > 5:
        raise ValueError('Máximo 5 cuotas programadas.')
    return plan


def apply_quota_plan_to_sale_and_ctas(sale, ctascollect, plan):
    inicial_row = next((row for row in plan if row['num'] == 0), None)
    regular = [row for row in plan if row['num'] > 0]
    sale.quota_plan_override = plan
    sale.credit_down_payment = _money(inicial_row['amount']) if inicial_row else Decimal('0.00')
    sale.credit_quota_count = len(regular)
    last_due = max(parse_date(row['due_date']) for row in plan)
    sale.end_credit = last_due
    sale.save(update_fields=[
        'quota_plan_override',
        'credit_down_payment',
        'credit_quota_count',
        'end_credit',
    ])
    ctascollect.end_date = last_due
    ctascollect.save(update_fields=['end_date'])
