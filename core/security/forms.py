from django import forms
from django.forms import ModelForm

from .models import *


class ModuleTypeForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = ModuleType
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
            'icon': forms.TextInput(attrs={'placeholder': 'ingrese un icono de font awesone'}),
        }
        exclude = []

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


class ModuleForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['url'].widget.attrs['autofocus'] = True

    class Meta:
        model = Module
        fields = '__all__'
        widgets = {
            'url': forms.TextInput(attrs={'placeholder': 'Ingrese una url'}),
            'moduletype': forms.Select(
                attrs={'class': 'form-control select2', 'required': False, 'style': 'width:100%'}),
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
            'description': forms.TextInput(attrs={'placeholder': 'Ingrese una descripción'}),
            'icon': forms.TextInput(attrs={'placeholder': 'ingrese un icono de font awesone'}),
            'permits': forms.SelectMultiple(
                attrs={'class': 'form-control select2', 'multiple': 'multiple', 'style': 'width:100%'}),
        }
        exclude = []

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


class GroupForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = Group
        fields = 'name',
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
        }
        exclude = ['modules']


class DashboardForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['layout'].widget.attrs['autofocus'] = True

    class Meta:
        model = Dashboard
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
            'icon': forms.TextInput(attrs={'placeholder': 'Ingrese un icono de font awesome'}),
            'layout': forms.Select(attrs={'class': 'form-control select2', 'style': 'width:100%'}),
            'navbar': forms.Select(attrs={'class': 'form-control select2', 'style': 'width:100%'}),
            'brand_logo': forms.Select(attrs={'class': 'form-control select2', 'style': 'width:100%'}),
            'card': forms.Select(attrs={'class': 'form-control select2', 'style': 'width:100%'}),
            'sidebar': forms.Select(attrs={'class': 'form-control select2', 'style': 'width:100%'}),
        }

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


class DniApiConfigurationForm(ModelForm):
    api_token_input = forms.CharField(
        required=False,
        label='API Key / Token',
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                'class': 'form-control',
                'autocomplete': 'new-password',
                'placeholder': 'Dejar vacío para mantener el token actual',
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['provider_name'].widget.attrs['autofocus'] = True
        if self.instance and self.instance.pk and self.instance.token_configured():
            self.fields['api_token_input'].help_text = (
                'Token guardado. Escriba uno nuevo solo si desea cambiarlo.'
            )

    class Meta:
        model = DniApiConfiguration
        fields = ['provider_name', 'api_url', 'api_timeout', 'is_enabled', 'notes']
        widgets = {
            'provider_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Decolecta',
            }),
            'api_url': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://api.ejemplo.com/dni?numero={dni}',
            }),
            'api_timeout': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 3,
                'max': 60,
            }),
            'is_enabled': forms.CheckboxInput(attrs={'class': ''}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Cuenta, contacto del proveedor, etc.',
            }),
        }

    def clean_api_url(self):
        url = (self.cleaned_data.get('api_url') or '').strip()
        if not url:
            raise forms.ValidationError('Ingrese la URL de consulta')
        if '{dni}' not in url:
            raise forms.ValidationError('La URL debe incluir el marcador {dni}')
        return url

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                new_token = (self.cleaned_data.get('api_token_input') or '').strip()
                if new_token:
                    self.instance.api_token = new_token
                super().save()
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data
