import json

from django.contrib.auth.models import Group
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, TemplateView

from config import settings
from core.pos.forms import ClientForm, User, Client
from core.pos.dni_lookup import lookup_dni_data
from core.pos.client_properties import (
    client_predios_template_context,
    save_client_properties_from_request,
)
from core.security.mixins import ModuleMixin, PermissionMixin, SupervisorDeleteApprovalMixin


class ClientListView(PermissionMixin, TemplateView):
    template_name = 'crm/client/list.html'
    permission_required = 'view_client'

    def post(self, request, *args, **kwargs):
        data = []
        try:
            action = request.POST.get('action', '')
            if action == 'search':
                for i in Client.objects.all():
                    data.append(i.toJSON())
            else:
                data = {'error': 'Acción no válida'}
        except Exception as e:
            import traceback
            data = {'error': str(e), 'trace': traceback.format_exc()}
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('client_create')
        context['title'] = 'Listado de Clientes'
        return context


class ClientCreateView(PermissionMixin, CreateView):
    model = Client
    template_name = 'crm/client/create.html'
    form_class = ClientForm
    success_url = reverse_lazy('client_list')
    permission_required = 'add_client'

    def validate_data(self):
        data = {'valid': True}
        try:
            type = self.request.POST['type']
            obj = self.request.POST['obj'].strip()
            if type == 'dni':
                if User.objects.filter(dni=obj):
                    data['valid'] = False
            elif type == 'mobile':
                if Client.objects.filter(mobile=obj):
                    data['valid'] = False
            elif type == 'email':
                if obj and User.objects.filter(email__iexact=obj).exists():
                    data['valid'] = False
        except:
            pass
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                with transaction.atomic():
                    user = User()
                    user.first_name = request.POST['first_name']
                    user.last_name = request.POST['last_name']
                    user.dni = request.POST['dni']
                    user.username = user.dni
                    '''if 'image' in request.FILES:
                        user.image = request.FILES['image']'''
                    user.create_or_update_password(user.dni)
                    user.email = (request.POST.get('email') or '').strip()
                    user.save()

                    client = Client()
                    client.user_id = user.id
                    client.mobile = request.POST['mobile']
                    client.department = (request.POST.get('department') or '').strip()
                    client.province = (request.POST.get('province') or '').strip()
                    client.district = (request.POST.get('district') or '').strip()
                    client.address = request.POST['address']
                    client.save()
                    try:
                        save_client_properties_from_request(
                            request,
                            client,
                            request.POST.get('properties_json', '[]'),
                        )
                    except ValueError as exc:
                        data['error'] = str(exc)
                        return HttpResponse(json.dumps(data), content_type='application/json')

                    group = Group.objects.get(pk=settings.GROUPS.get('client'))
                    user.groups.add(group)
            elif action == 'validate_data':
                return self.validate_data()
            elif action == 'lookup_dni':
                payload = lookup_dni_data(request.POST.get('dni', ''))
                if payload.get('error'):
                    return JsonResponse({'success': False, 'error': payload['error']})
                return JsonResponse({'success': True, 'data': payload})
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de un Cliente'
        context['action'] = 'add'
        context['instance'] = None
        context.update(client_predios_template_context())
        return context


class ClientUpdateView(PermissionMixin, UpdateView):
    model = Client
    template_name = 'crm/client/create.html'
    form_class = ClientForm
    success_url = reverse_lazy('client_list')
    permission_required = 'change_client'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        instance = self.object
        form = ClientForm(instance=instance, initial={
            'first_name': instance.user.first_name,
            'last_name': instance.user.last_name,
            'dni': instance.user.dni,
            'email': instance.user.email or '',
        })
        return form

    def validate_data(self):
        data = {'valid': True}
        try:
            instance = self.object
            type = self.request.POST['type']
            obj = self.request.POST['obj'].strip()
            if type == 'dni':
                if User.objects.filter(dni=obj).exclude(id=instance.user.id):
                    data['valid'] = False
            elif type == 'mobile':
                if Client.objects.filter(mobile=obj).exclude(id=instance.id):
                    data['valid'] = False
            elif type == 'email':
                if obj and User.objects.filter(email__iexact=obj).exclude(id=instance.user.id).exists():
                    data['valid'] = False
        except:
            pass
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    instance = self.object
                    user = instance.user
                    user.first_name = request.POST['first_name']
                    user.last_name = request.POST['last_name']
                    user.dni = request.POST['dni']
                    user.username = user.dni
                    user.email = (request.POST.get('email') or '').strip()
                    user.save()

                    client = instance
                    client.user_id = user.id
                    client.mobile = request.POST['mobile']
                    client.department = (request.POST.get('department') or '').strip()
                    client.province = (request.POST.get('province') or '').strip()
                    client.district = (request.POST.get('district') or '').strip()
                    client.address = request.POST['address']
                    client.save()
                    try:
                        save_client_properties_from_request(
                            request,
                            client,
                            request.POST.get('properties_json', '[]'),
                        )
                    except ValueError as exc:
                        data['error'] = str(exc)
                        return HttpResponse(json.dumps(data), content_type='application/json')
            elif action == 'validate_data':
                return self.validate_data()
            elif action == 'lookup_dni':
                payload = lookup_dni_data(request.POST.get('dni', ''))
                if payload.get('error'):
                    return JsonResponse({'success': False, 'error': payload['error']})
                return JsonResponse({'success': True, 'data': payload})
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Edición de un Cliente'
        context['action'] = 'edit'
        context['instance'] = self.object
        context.update(client_predios_template_context(self.object))
        return context


class ClientDeleteView(SupervisorDeleteApprovalMixin, PermissionMixin, DeleteView):
    model = Client
    template_name = 'crm/client/delete.html'
    success_url = reverse_lazy('client_list')
    permission_required = 'delete_client'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            with transaction.atomic():
                instance = self.get_object()
                user = instance.user
                instance.delete()
                user.delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notificación de eliminación'
        context['list_url'] = self.success_url
        return context


class ClientUpdateProfileView(ModuleMixin, UpdateView):
    model = Client
    template_name = 'crm/client/profile.html'
    form_class = ClientForm
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user.client

    def get_form(self, form_class=None):
        instance = self.object
        form = ClientForm(instance=instance, initial={
            'first_name': instance.user.first_name,
            'last_name': instance.user.last_name,
            'dni': instance.user.dni,
            'email': instance.user.email or '',
        })
        return form

    def validate_data(self):
        data = {'valid': True}
        try:
            instance = self.object
            type = self.request.POST['type']
            obj = self.request.POST['obj'].strip()
            if type == 'dni':
                if User.objects.filter(dni=obj).exclude(id=instance.user.id):
                    data['valid'] = False
            elif type == 'mobile':
                if Client.objects.filter(mobile=obj).exclude(id=instance.id):
                    data['valid'] = False
            elif type == 'email':
                if obj and User.objects.filter(email__iexact=obj).exclude(id=instance.user.id).exists():
                    data['valid'] = False
        except:
            pass
        return JsonResponse(data)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    instance = self.object
                    user = instance.user
                    user.first_name = request.POST['first_name']
                    user.last_name = request.POST['last_name']
                    user.dni = request.POST['dni']
                    user.username = user.dni
                    user.email = (request.POST.get('email') or '').strip()
                    user.save()

                    client = instance
                    client.user_id = user.id
                    client.mobile = request.POST['mobile']
                    client.department = (request.POST.get('department') or '').strip()
                    client.province = (request.POST.get('province') or '').strip()
                    client.district = (request.POST.get('district') or '').strip()
                    client.address = request.POST['address']
                    client.save()
                    try:
                        save_client_properties_from_request(
                            request,
                            client,
                            request.POST.get('properties_json', '[]'),
                        )
                    except ValueError as exc:
                        data['error'] = str(exc)
                        return HttpResponse(json.dumps(data), content_type='application/json')
            elif action == 'validate_data':
                return self.validate_data()
            elif action == 'lookup_dni':
                payload = lookup_dni_data(request.POST.get('dni', ''))
                if payload.get('error'):
                    return JsonResponse({'success': False, 'error': payload['error']})
                return JsonResponse({'success': True, 'data': payload})
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['list_url'] = self.success_url
        context['title'] = 'Edición de Perfil'
        context['action'] = 'edit'
        context['instance'] = self.object
        context.update(client_predios_template_context(self.object))
        return context
