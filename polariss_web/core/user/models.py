# -*- coding: utf-8 -*-
import uuid

from crum import get_current_request
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario personalizado — misma idea que Factora (campos mínimos para login / recuperación)."""

    dni = models.CharField(max_length=13, unique=True, blank=True, null=True, verbose_name='Dni / documento')
    is_change_password = models.BooleanField(default=False)
    token = models.UUIDField(primary_key=False, editable=False, null=True, blank=True, default=uuid.uuid4, unique=True)

    def generate_token(self):
        return uuid.uuid4()

    def set_group_session(self):
        try:
            request = get_current_request()
            groups = request.user.groups.all()
            if groups and 'group' not in request.session:
                request.session['group'] = groups[0]
        except Exception:
            pass

    class Meta:
        app_label = 'user'

    def __str__(self):
        return self.get_full_name() or self.username
