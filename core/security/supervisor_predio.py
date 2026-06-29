"""Autorización para desvincular predios con contrato generado."""

from core.security.role_groups import user_has_supervisor_access


def user_can_authorize_predio_unlock(user):
    if not user or not getattr(user, 'is_active', False):
        return False
    if user_has_supervisor_access(user):
        return True
    return user.has_perm('pos.unlock_contract_predio')
