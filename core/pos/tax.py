from decimal import Decimal, ROUND_HALF_UP


def split_tax_inclusive(amount, rate):
    """
    Descompone un monto que ya incluye impuesto (IGV).

    amount: total con impuesto incluido (ej. 1500.00)
    rate: tasa decimal (0.18 para 18 %)

    Returns (base_imponible, monto_impuesto)
    """
    amount = Decimal(str(amount))
    rate = Decimal(str(rate))
    if rate <= 0:
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), Decimal('0.00')
    base = (amount / (1 + rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    tax = (amount - base).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return base, tax
