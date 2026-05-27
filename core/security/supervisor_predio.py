"""Autorización para desvincular predios con contrato generado."""


def user_can_authorize_predio_unlock(user):
    if not user or not getattr(user, 'is_active', False):
        return False
    if user.is_superuser:
        return True
    return user.has_perm('pos.unlock_contract_predio')
