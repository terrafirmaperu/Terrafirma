# -*- coding: utf-8 -*-
import re

from django.db.models import Q

from core.pos.models import Client

ADVISORY_STAGE_MIN = 2
ADVISORY_STAGE_MAX = 9
DNI_SEARCH_MIN_LEN = 2


def normalize_dni(value):
    """Solo dígitos (DNI/RUC sin guiones ni espacios)."""
    return re.sub(r'\D', '', (value or '').strip())


def client_to_lookup_dict(client):
    user = client.user
    from core.pos.models import AdvisoryProgressCase

    return {
        'id': client.id,
        'client_code': client.client_code or '',
        'full_name': user.get_full_name() or user.get_username(),
        'dni': user.dni or '',
        'has_predio': bool(client.has_predio),
        'predio_summary': AdvisoryProgressCase.build_predio_summary(client),
    }


def find_clients_by_dni(dni_input, limit=20):
    """
    Busca clientes por DNI, código de cliente o nombre.
    Incluye coincidencia parcial desde 2 caracteres y comparación solo numérica.
    """
    raw = (dni_input or '').strip()
    digits = normalize_dni(raw)
    if len(digits) < DNI_SEARCH_MIN_LEN and len(raw) < DNI_SEARCH_MIN_LEN:
        return []

    base = Client.objects.select_related('user')
    found = []
    seen = set()

    def add_client(c):
        if c.id not in seen and len(found) < limit:
            seen.add(c.id)
            found.append(c)

    q = Q()
    if len(raw) >= DNI_SEARCH_MIN_LEN:
        q |= Q(user__dni__icontains=raw)
        q |= Q(user__username__icontains=raw)
        q |= Q(client_code__icontains=raw)
        q |= Q(user__first_name__icontains=raw)
        q |= Q(user__last_name__icontains=raw)
    if len(digits) >= DNI_SEARCH_MIN_LEN:
        q |= Q(user__dni__icontains=digits)
        q |= Q(user__username__icontains=digits)
        q |= Q(client_code__icontains=digits)

    if q:
        for c in base.filter(q).distinct().order_by('user__dni')[:limit]:
            add_client(c)

    # Coincidencia numérica aunque el DNI tenga espacios o guiones guardados
    if len(digits) >= DNI_SEARCH_MIN_LEN and len(found) < limit:
        for c in base.exclude(pk__in=seen).order_by('id')[:500]:
            u = c.user
            stored = normalize_dni(u.dni)
            stored_user = normalize_dni(u.username)
            if digits in stored or digits in stored_user:
                add_client(c)
            if len(found) >= limit:
                break

    return found


def find_client_by_dni_exact(dni_input):
    """Un cliente si hay coincidencia exacta; si no, el único resultado parcial."""
    clients = find_clients_by_dni(dni_input, limit=20)
    if not clients:
        return None
    digits = normalize_dni(dni_input)
    raw = (dni_input or '').strip()
    for c in clients:
        u = c.user
        if raw and (u.dni or '').strip().lower() == raw.lower():
            return c
        if digits and normalize_dni(u.dni) == digits:
            return c
        if digits and normalize_dni(u.username) == digits:
            return c
    return clients[0] if len(clients) == 1 else None


def clamp_stage_count(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = ADVISORY_STAGE_MIN
    return max(ADVISORY_STAGE_MIN, min(ADVISORY_STAGE_MAX, n))
