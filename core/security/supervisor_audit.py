# -*- coding: utf-8 -*-
"""Registro de autorizaciones y acciones sensibles (supervisor Neo)."""

import json

from django.contrib.auth import get_user_model

User = get_user_model()

EVENT_LABELS = {
    'authorize_delete': 'Autorización: eliminar registros',
    'authorize_quota_edit': 'Autorización: modificar cuotas CxC',
    'authorize_collector': 'Autorización: Admin Cobranzas',
    'authorize_collector_save': 'Autorización: guardar cobrador',
    'authorize_predio_unlock': 'Autorización: desvincular predio con contrato',
    'action_delete': 'Eliminación ejecutada',
    'action_quota_plan': 'Cuotas modificadas en CxC',
    'action_collector_save': 'Cobrador registrado o actualizado',
    'action_predio_unlock': 'Predio con contrato desvinculado',
    'action_devolution_refund': 'Devolución con reembolso autorizada',
}

AUTH_CHANGE_HINTS = {
    'authorize_delete': 'Autorizó eliminar un registro (falta confirmar el borrado).',
    'authorize_quota_edit': 'Autorizó modificar montos y fechas de cuotas en CxC.',
    'authorize_collector': 'Autorizó ingresar al módulo Admin Cobranzas.',
    'authorize_collector_save': 'Autorizó crear o editar un cobrador.',
    'authorize_predio_unlock': 'Autorizó desvincular predio(s) con contrato generado.',
}

SESSION_AUTHORIZER_PREFIX = 'supervisor_auth_user_'


def is_neo_user(user):
    return bool(user and getattr(user, 'is_authenticated', False) and user.username == 'Neo')


def _client_ip(request):
    if not request:
        return ''
    info = request.session.get('infobyip') or {}
    ip = (info.get('ipaddress') or '').strip()
    if ip:
        return ip
    from core.user.models import client_ip_from_request
    return client_ip_from_request(request) or ''


def format_quota_plan(plan):
    if not plan:
        return 'Sin plan personalizado'
    if isinstance(plan, str):
        try:
            plan = json.loads(plan)
        except (json.JSONDecodeError, TypeError):
            return plan[:500]
    if not isinstance(plan, list):
        return str(plan)[:500]
    parts = []
    for row in plan:
        if not isinstance(row, dict):
            continue
        label = row.get('label') or ('Cuota {}'.format(row.get('num', '?')))
        amount = row.get('amount', '0')
        due = row.get('due_date', '—')
        parts.append('{} S/ {} (vence {})'.format(label, amount, due))
    return ' · '.join(parts) if parts else 'Plan vacío'


def describe_deleted_object(obj):
    if obj is None:
        return 'Registro eliminado'
    model = obj.__class__.__name__
    try:
        from core.pos.models import Sale, Client, CtasCollect, Collector, Product, ClientProperty
        if isinstance(obj, Sale):
            code = getattr(obj, 'sale_code', '') or obj.pk
            client_name = ''
            if obj.client_id and obj.client.user_id:
                client_name = obj.client.user.get_full_name() or obj.client.user.username
            return 'Venta {} — Cliente: {} — Total S/ {}'.format(
                code, client_name or '—', obj.total,
            )
        if isinstance(obj, Client):
            u = obj.user
            return 'Cliente {} ({}) — DNI {}'.format(
                u.get_full_name() or u.username,
                obj.client_code or 'sin código',
                u.dni or '—',
            )
        if isinstance(obj, CtasCollect):
            sale = obj.sale
            sale_ref = sale.pk
            if sale:
                sale_ref = getattr(sale, 'sale_code', None) or sale.pk
            return 'CxC #{} — Venta {} — Saldo S/ {}'.format(
                obj.pk, sale_ref, obj.saldo,
            )
        if isinstance(obj, Collector):
            return 'Cobrador «{}»'.format(obj.name)
        if isinstance(obj, Product):
            return 'Producto «{}»'.format(obj.name)
        if isinstance(obj, ClientProperty):
            return 'Predio «{}» del cliente #{}'.format(str(obj), obj.client_id)
    except Exception:
        pass
    text = str(obj).strip()
    if text:
        return '{}: {}'.format(model, text[:200])
    return '{} id={}'.format(model, getattr(obj, 'pk', '—'))


def store_supervisor_authorizer(request, session_key, supervisor_user):
    if not request or not supervisor_user:
        return
    request.session[f'{SESSION_AUTHORIZER_PREFIX}{session_key}'] = supervisor_user.pk
    request.session.modified = True


def pop_supervisor_authorizer(request, session_key):
    if not request:
        return None
    uid = request.session.pop(f'{SESSION_AUTHORIZER_PREFIX}{session_key}', None)
    request.session.modified = True
    if not uid:
        return None
    return User.objects.filter(pk=uid).first()


def log_supervisor_event(
    request,
    event_type,
    *,
    category='accion',
    summary='',
    detail='',
    change_summary='',
    supervisor_user=None,
    object_type='',
    object_id='',
):
    from core.security.models import SupervisorAuditLog

    if not summary:
        summary = EVENT_LABELS.get(event_type, event_type)

    actor = None
    if request and getattr(request, 'user', None) and request.user.is_authenticated:
        actor = request.user

    SupervisorAuditLog.objects.create(
        category=category,
        event_type=event_type,
        summary=summary[:255],
        detail=(detail or '')[:5000],
        change_summary=(change_summary or detail or summary or '')[:5000],
        actor_user=actor,
        supervisor_user=supervisor_user,
        ip_address=_client_ip(request)[:45] if request else '',
        request_path=(request.path if request else '')[:500],
        object_type=(object_type or '')[:120],
        object_id=str(object_id or '')[:80],
    )


def log_supervisor_authorization(request, session_key, event_type, supervisor_user, extra_detail=''):
    store_supervisor_authorizer(request, session_key, supervisor_user)
    change = AUTH_CHANGE_HINTS.get(event_type, 'Autorización de supervisor.')
    detail_parts = [
        'Usuario en sesión: {}'.format(
            request.user.get_full_name() or request.user.username
            if request.user.is_authenticated else '—'
        ),
        'Supervisor que autorizó: {}'.format(
            supervisor_user.get_full_name() or supervisor_user.username
        ),
    ]
    if extra_detail:
        detail_parts.append(extra_detail)
    log_supervisor_event(
        request,
        event_type,
        category='autorizacion',
        detail=' · '.join(detail_parts),
        change_summary=change,
        supervisor_user=supervisor_user,
    )
