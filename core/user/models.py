# -*- coding: utf-8 -*-
import os
import uuid

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from crum import get_current_request
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms.models import model_to_dict

from config import settings


def client_ip_from_request(request):
    """IP del navegador/dispositivo vista por Django (X-Forwarded-For o REMOTE_ADDR)."""
    if not request:
        return ''
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or '').strip()


class User(AbstractUser):
    dni = models.CharField(max_length=13, unique=True, verbose_name='Dni, RUC ó Cédula')
    is_change_password = models.BooleanField(default=False)
    token = models.UUIDField(primary_key=False, editable=False, null=True, blank=True, default=uuid.uuid4, unique=True)

    def toJSON(self):
        item = model_to_dict(self, exclude=['last_login', 'token', 'password', 'user_permissions'])
        dj = item.get('date_joined')
        if dj is not None:
            item['date_joined'] = dj.strftime('%Y-%m-%d') if hasattr(dj, 'strftime') else str(dj)
        item['full_name'] = self.get_full_name()
        item['groups'] = self.get_groups()
        item['last_login'] = None if self.last_login is None else self.last_login.strftime('%Y-%m-%d')
        return item

    def generate_token(self):
        return uuid.uuid4()

    def get_groups(self):
        data = []
        for i in self.groups.all():
            data.append({'id': i.id, 'name': i.name})
        return data

    def get_group_id_session(self):
        try:
            request = get_current_request()
            from core.security.session_group import get_group_from_session
            group = get_group_from_session(request)
            return int(group.pk) if group else 0
        except Exception:
            return 0

    def set_group_session(self):
        try:
            request = get_current_request()
            groups = request.user.groups.all()
            if groups:
                request.session['infobyip'] = self.infobyip(request)
                from core.security.session_group import set_group_id_in_session
                set_group_id_in_session(request, groups[0])
        except Exception:
            pass

    def create_or_update_password(self, password):
        try:
            if self.pk is None:
                self.set_password(password)
            else:
                user = User.objects.get(pk=self.pk)
                if user.password != password:
                    self.set_password(password)
        except:
            pass

    def is_client(self):
        try:
            if hasattr(self, 'client'):
                return True
        except:
            pass
        return False

    def infobyip(self, request=None):
        """IP del dispositivo cliente + datos de ubicación/ISP de esa IP (no la del servidor)."""
        response = {'ipaddress': '', 'location': '', 'isp': '', 'countrycode': ''}
        if request is None:
            try:
                request = get_current_request()
            except Exception:
                request = None
        client_ip = client_ip_from_request(request)
        response['ipaddress'] = client_ip
        if not client_ip or requests is None:
            return response
        if client_ip in ('127.0.0.1', '::1'):
            return response
        try:
            r = requests.get(
                f'http://ip-api.com/json/{client_ip}',
                params={'fields': 'status,message,country,countryCode,isp,city'},
                timeout=4,
            )
            if r.status_code != 200:
                return response
            data = r.json()
            if data.get('status') != 'success':
                return response
            city = (data.get('city') or '').strip()
            country = (data.get('country') or '').strip()
            response['location'] = ', '.join(p for p in (city, country) if p)
            response['isp'] = (data.get('isp') or '').strip()
            response['countrycode'] = (data.get('countryCode') or '').strip()
        except Exception:
            pass
        return response

    def __str__(self):
        return self.get_full_name()
