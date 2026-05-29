from django import forms
from django.contrib.auth.forms import AuthenticationForm

from core.user.models import User


class CaseInsensitiveAuthenticationForm(AuthenticationForm):
    """Acepta neo/Neo y evita espacios accidentales en usuario o contraseña."""

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            return username
        user = User.objects.filter(username__iexact=username).first()
        if user:
            return user.username
        return username

    def clean_password(self):
        return (self.cleaned_data.get('password') or '').strip()


class ResetPasswordForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Ingrese un username',
        'class': 'form-control',
        'autocomplete': 'off'
    }))

    def clean(self):
        cleaned = super().clean()
        users = User.objects.filter(username=cleaned['username'])
        if not users.exists():
            raise forms.ValidationError('El username no existe')
            #self._errors['error'] = self._errors.get('error', self.error_class())
            #self._errors['error'].append('El username no existe')
        return cleaned

    def get_user(self):
        username = self.cleaned_data.get('username')
        return User.objects.get(username=username)


class ChangePasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Ingrese un password',
        'class': 'form-control',
        'autocomplete': 'off'
    }))
    confirmPassword = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Repita el password',
        'class': 'form-control',
        'autocomplete': 'off'
    }))

    def clean(self):
        cleaned = super().clean()
        password = cleaned['password']
        confirmPassword = cleaned['confirmPassword']
        if password != confirmPassword:
            raise forms.ValidationError('Las contraseñas deben ser iguales')
        return cleaned
