# -*- coding: utf-8 -*-
from django import forms

SERVICE_CHOICES = (
    ('', 'Seleccione…'),
    ('titulacion', 'Titulación predial'),
    ('municipales', 'Asesorías municipales'),
    ('topografia', 'Topografía e ingeniería'),
    ('vivienda', 'Fondo Mi Vivienda / Techo Propio'),
    ('otro', 'Otro'),
)


class ClientePortalLoginForm(forms.Form):
    dni = forms.CharField(
        label='DNI / documento',
        max_length=13,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 12345678',
                'autocomplete': 'username',
            }
        ),
    )
    client_code = forms.CharField(
        label='Código de cliente',
        max_length=20,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Código asignado por la empresa',
                'autocomplete': 'off',
            }
        ),
    )


class MarketingContactForm(forms.Form):
    name = forms.CharField(
        label='Nombre completo',
        max_length=120,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Su nombre',
                'id': 'contact-name',
                'autocomplete': 'name',
            }
        ),
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
                'id': 'contact-email',
                'autocomplete': 'email',
            }
        ),
    )
    phone = forms.CharField(
        label='Teléfono',
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '921 047 681',
                'id': 'contact-phone',
                'autocomplete': 'tel',
            }
        ),
    )
    service = forms.ChoiceField(
        label='Servicio de interés',
        choices=SERVICE_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
                'id': 'contact-service',
            }
        ),
    )
    message = forms.CharField(
        label='Mensaje',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describa su predio, ubicación y qué necesita…',
                'id': 'contact-message',
            }
        ),
    )
