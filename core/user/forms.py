from crum import get_current_request
from django import forms
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import Group
from django.db.models import Case, IntegerField, Value, When
from django.forms import ModelForm

from core.security.role_groups import DEFAULT_USER_GROUP_NAMES, assign_supervisor_group_only
from core.user.neo_owner import NEO_USERNAME

from .models import User


class UserForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['groups'].required = True
        self.fields['first_name'].widget.attrs['autofocus'] = True
        order = {name: idx for idx, name in enumerate(DEFAULT_USER_GROUP_NAMES)}
        whens = [When(name=name, then=Value(order[name])) for name in DEFAULT_USER_GROUP_NAMES]
        self.fields['groups'].queryset = (
            Group.objects.filter(name__in=DEFAULT_USER_GROUP_NAMES)
            .annotate(
                sort_order=Case(
                    *whens,
                    default=Value(99),
                    output_field=IntegerField(),
                )
            )
            .order_by('sort_order', 'name')
        )
        self.fields['groups'].help_text = (
            'Supervisor: acceso total (todos los módulos, Mensajería WhatsApp, crear, editar y eliminar). '
            'Administrador y Asistente: sin Mensajería ni Seguridad completa. '
            'Administrador: vende y cobra como Asistente, consulta el resto. '
            'Asistente: solo ventas y cobros. Cliente: portal del cliente.'
        )

    class Meta:
        model = User
        #fields = 'first_name', 'last_name', 'username', 'password', 'dni', 'email', 'groups', 'image', 'is_active'
        fields = 'first_name', 'last_name', 'username', 'password', 'dni', 'email', 'groups', 'is_active'
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Ingrese sus nombres'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Ingrese sus apellidos'}),
            'username': forms.TextInput(attrs={'placeholder': 'Ingrese un username'}),
            'dni': forms.TextInput(attrs={'placeholder': 'Ingrese su número de Dni o Cédula', 'maxlength': '8'}),
            'email': forms.TextInput(attrs={'placeholder': 'Ingrese su correo electrónico'}),
            'password': forms.PasswordInput(render_value=True, attrs={'placeholder': 'Ingrese un password'}),
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'multiple': 'multiple', 'style': 'width:100%'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-control-checkbox'})
        }
        exclude = ['is_change_password', 'is_staff', 'user_permissions', 'date_joined',
                   'last_login', 'is_superuser', 'token']

    def update_session(self, user):
        request = get_current_request()
        if user == request.user:
            update_session_auth_hash(request, user)

    def save(self, commit=True):
        data = {}
        form = super()
        try:
            if form.is_valid():
                pwd = self.cleaned_data['password']
                u = form.save(commit=False)
                if u.pk is None:
                    u.set_password(pwd)
                else:
                    user = User.objects.get(pk=u.pk)
                    if user.password != pwd:
                        u.set_password(pwd)
                u.save()

                u.groups.clear()
                for g in self.cleaned_data['groups']:
                    u.groups.add(g)

                if u.username == NEO_USERNAME:
                    u.is_active = True
                    u.is_staff = True
                    u.is_superuser = True
                    u.save(update_fields=['is_active', 'is_staff', 'is_superuser'])
                    assign_supervisor_group_only(u)

                self.update_session(u)
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class ProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['autofocus'] = True

    class Meta:
        model = User
        #fields = 'first_name', 'last_name', 'username', 'dni', 'email'
        fields = 'first_name', 'last_name', 'username', 'dni'
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Ingrese sus nombres'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Ingrese sus apellidos'}),
            'username': forms.TextInput(attrs={'placeholder': 'Ingrese un username'}),
            #'dni': forms.TextInput(attrs={'placeholder': 'Ingrese su número de Dni ó Cédula'}),
            'email': forms.TextInput(attrs={'placeholder': 'Ingrese su correo electrónico'}),
        }
        exclude = ['is_change_password', 'is_active', 'is_staff', 'user_permissions', 'password', 'date_joined',
                   'last_login', 'is_superuser', 'groups', 'token']

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                super().save()
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data
