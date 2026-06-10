import json

from django import forms
from django.forms import ModelForm

from core.whatsapp.models import WhatsAppApiConfiguration, WhatsAppBulkMessage
from core.whatsapp.whatsapp_recipients import AUDIENCE_CHOICES, build_filter_criteria_from_post


class WhatsAppApiConfigurationForm(ModelForm):
    api_token_input = forms.CharField(
        label='Token de acceso (permanente)',
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={
            'class': 'form-control',
            'placeholder': 'Token de Meta / WhatsApp Cloud API',
            'autocomplete': 'new-password',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['provider_name'].widget.attrs['autofocus'] = True
        if self.instance and self.instance.pk and self.instance.token_configured():
            self.fields['api_token_input'].help_text = (
                'Token guardado. Escriba uno nuevo solo si desea cambiarlo.'
            )

    class Meta:
        model = WhatsAppApiConfiguration
        fields = [
            'provider_name',
            'phone_number_id',
            'phone_number_display',
            'business_account_id',
            'api_base_url',
            'api_version',
            'api_timeout',
            'is_enabled',
            'notes',
        ]
        widgets = {
            'provider_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID del número en Meta Business',
            }),
            'phone_number_display': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 921047681',
            }),
            'business_account_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Opcional — WABA ID',
            }),
            'api_base_url': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://graph.facebook.com',
            }),
            'api_version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'v21.0',
            }),
            'api_timeout': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'max': 120}),
            'is_enabled': forms.CheckboxInput(attrs={'class': ''}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_phone_number_id(self):
        value = (self.cleaned_data.get('phone_number_id') or '').strip()
        if not value:
            raise forms.ValidationError('Ingrese el Phone Number ID de Meta.')
        return value

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


class WhatsAppBulkMessageForm(ModelForm):
    class Meta:
        model = WhatsAppBulkMessage
        fields = ['name', 'message_body', 'recipient_source', 'recipients_text', 'filter_criteria']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Aviso de cierre administrativo',
            }),
            'message_body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Texto del mensaje masivo…',
            }),
            'recipient_source': forms.Select(attrs={'class': 'form-control'}),
            'recipients_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': '921047681\n987654321',
            }),
            'filter_criteria': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self._filter_post = kwargs.pop('filter_post', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        source = cleaned.get('recipient_source')
        text = (cleaned.get('recipients_text') or '').strip()
        if source == WhatsAppBulkMessage.SOURCE_MANUAL and not text:
            self.add_error('recipients_text', 'Ingrese al menos un número para envío manual.')
        body = (cleaned.get('message_body') or '').strip()
        if not body:
            self.add_error('message_body', 'Escriba el mensaje a enviar.')
        if source == WhatsAppBulkMessage.SOURCE_FILTER:
            criteria = build_filter_criteria_from_post(self._filter_post or {})
            cleaned['filter_criteria'] = json.dumps(criteria, ensure_ascii=False)
        elif source != WhatsAppBulkMessage.SOURCE_FILTER:
            cleaned['filter_criteria'] = '{}'
        return cleaned

    def save(self, commit=True, user=None):
        data = {}
        try:
            if self.is_valid():
                if user is not None:
                    self.instance.user = user
                if self.cleaned_data.get('filter_criteria') is not None:
                    self.instance.filter_criteria = self.cleaned_data['filter_criteria']
                super().save()
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data
