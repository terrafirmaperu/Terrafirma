from django.forms import ModelForm
from django import forms
from django.utils import timezone

from .models import *


class CategoryForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = Category
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
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


class ProductForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = Product
        fields = ['name', 'category', 'pvp']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
            'category': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'pvp': forms.TextInput(),
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


class PurchaseForm(ModelForm):
    class Meta:
        model = Purchase
        fields = '__all__'
        widgets = {
            'payment_condition': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'date_joined': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'date_joined',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#date_joined'
            }),
            'end_credit': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'end_credit',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#end_credit'
            }),
            'subtotal': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off'
            }),
        }


class TypeExpenseForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True

    class Meta:
        model = TypeExpense
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
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


class ExpensesForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['typeexpense'].widget.attrs['autofocus'] = True

    class Meta:
        model = Expenses
        fields = '__all__'
        widgets = {
            'typeexpense': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'desc': forms.Textarea(attrs={'placeholder': 'Ingrese una descripción', 'rows': 3, 'cols': '3'}),
            'date_joined': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'date_joined',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#date_joined'
            }),
            'valor': forms.TextInput()
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


class PaymentsDebtsPayForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['valor'].widget.attrs['autofocus'] = True
        self.fields['debtspay'].queryset = DebtsPay.objects.none()

    class Meta:
        model = PaymentsDebtsPay
        fields = '__all__'
        widgets = {
            'debtspay': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'date_joined': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'date_joined',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#date_joined'
            }),
            'valor': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
            }),
            'desc': forms.Textarea(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'rows': 3,
                'cols': 3,
                'placeholder': 'Ingrese una descripción'
            }),
        }


class ClientForm(ModelForm):
    PERU_DEPARTMENTS = (
        ('', 'Seleccione departamento'),
        ('Amazonas', 'Amazonas'),
        ('Ancash', 'Ancash'),
        ('Apurimac', 'Apurimac'),
        ('Arequipa', 'Arequipa'),
        ('Ayacucho', 'Ayacucho'),
        ('Cajamarca', 'Cajamarca'),
        ('Callao', 'Callao'),
        ('Cusco', 'Cusco'),
        ('Huancavelica', 'Huancavelica'),
        ('Huanuco', 'Huanuco'),
        ('Ica', 'Ica'),
        ('Junin', 'Junin'),
        ('La Libertad', 'La Libertad'),
        ('Lambayeque', 'Lambayeque'),
        ('Lima', 'Lima'),
        ('Loreto', 'Loreto'),
        ('Madre de Dios', 'Madre de Dios'),
        ('Moquegua', 'Moquegua'),
        ('Pasco', 'Pasco'),
        ('Piura', 'Piura'),
        ('Puno', 'Puno'),
        ('San Martin', 'San Martin'),
        ('Tacna', 'Tacna'),
        ('Tumbes', 'Tumbes'),
        ('Ucayali', 'Ucayali'),
    )

    """Datos de contacto en Client; nombres, dni y email viven en User (se copian en las vistas al guardar)."""

    first_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off',
        'placeholder': 'Ingrese sus nombres'
    }), label='Nombres', max_length=50)

    last_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off',
        'placeholder': 'Ingrese sus apellidos'
    }), label='Apellidos', max_length=50)

    dni = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off',
        'placeholder': 'Ingrese su número de Dni o Cédula',
        'minlength': '7',
        'maxlength': '12',
    }), label='Número de Dni ó Cédula', max_length=12)

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'autocomplete': 'email',
            'placeholder': 'Ingrese su correo electrónico'
        }),
        label='Email',
        max_length=254,
        required=False,
    )

    department = forms.ChoiceField(
        choices=PERU_DEPARTMENTS,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Departamento',
        required=False,
    )

    province = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
            'placeholder': 'Ingrese su provincia'
        }),
        label='Provincia',
        required=False,
        max_length=80,
    )

    district = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
            'placeholder': 'Ingrese su distrito'
        }),
        label='Distrito',
        required=False,
        max_length=80,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Client
        fields = [
            'mobile', 'department', 'province', 'district', 'address',
        ]
        widgets = {
            'mobile': forms.TextInput(
                attrs={
                    'placeholder': 'Ingrese su número celular',
                    'class': 'form-control',
                    'autocomplete': 'off'
                }
            ),
            'address': forms.TextInput(
                attrs={
                    'placeholder': 'Ingrese una dirección',
                    'class': 'form-control',
                    'autocomplete': 'off',
                }
            ),
        }

    field_order = [
        'first_name', 'last_name', 'dni', 'email', 'mobile',
        'department', 'province', 'district', 'address',
    ]


class SaleForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.all()

    class Meta:
        model = Sale
        exclude = (
            'credit_quota_count',
            'credit_down_payment',
            'credit_down_payment_method',
            'cash_register_session',
        )
        widgets = {
            'client': forms.Select(attrs={'class': 'custom-select select2'}),
            'payment_condition': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'payment_method': forms.Select(
                attrs={'class': 'form-control factora-pay-method-select d-none'}
            ),
            'type_voucher': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'date_joined': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'date_joined',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#date_joined'
            }),
            'end_credit': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'end_credit',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#end_credit'
            }),
            'subtotal': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'disabled': True
            }),
            'igv': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'disabled': True
            }),
            'total_igv': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'disabled': True
            }),
            'dscto': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'autocomplete': 'off'
            }),
            'total_dscto': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'disabled': True
            }),
            'total': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'disabled': True
            }),
            'cash': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'change': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'card_number': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': 'Ingrese el número de la tarjeta'
            }),
            'titular': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': 'Ingrese el nombre del titular'
            }),
            'amount_debited': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'readonly': True
            }),
        }

    amount = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off',
        'disabled': True
    }))


class PaymentsCtaCollectForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['valor'].widget.attrs['autofocus'] = True
        self.fields['ctascollect'].queryset = PaymentsCtaCollect.objects.none()

    class Meta:
        model = PaymentsCtaCollect
        exclude = ('cash_register_session',)
        widgets = {
            'ctascollect': forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 100%;'}),
            'date_joined': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'date_joined',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#date_joined'
            }),
            'valor': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
            }),
            'desc': forms.Textarea(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'rows': 3,
                'cols': 3,
                'placeholder': 'Ingrese una descripción'
            }),
        }


class CompanyForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['autofocus'] = True
        for form in self.visible_fields():
            form.field.widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'off'
            })

    class Meta:
        model = Company
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ingrese un nombre'}),
            'ruc': forms.TextInput(attrs={'placeholder': 'Ingrese un ruc'}),
            'mobile': forms.TextInput(attrs={'placeholder': 'Ingrese un teléfono celular'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Ingrese un teléfono convencional'}),
            'email': forms.TextInput(attrs={'placeholder': 'Ingrese un email'}),
            'address': forms.TextInput(attrs={'placeholder': 'Ingrese una dirección'}),
            'website': forms.TextInput(attrs={'placeholder': 'Ingrese una dirección web'}),
            'desc': forms.Textarea(attrs={'placeholder': 'Ingrese una descripción', 'rows': 3, 'cols': 3}),
            'igv': forms.TextInput(),
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


class PromotionsForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['end_date'].widget.attrs['autofocus'] = True

    class Meta:
        model = Promotions
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'start_date',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#start_date'
            }),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'end_date',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#end_date'
            }),
        }
        exclude = ['state']

    date_range = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off'
    }))


class DevolutionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_joined'].widget.attrs['autofocus'] = True

    class Meta:
        model = Devolution
        fields = '__all__'
        widgets = {
            'date_joined': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control datetimepicker-input',
                'id': 'start_date',
                'value': datetime.now().strftime('%Y-%m-%d'),
                'data-toggle': 'datetimepicker',
                'data-target': '#start_date'
            }),
        }

    sale = forms.ChoiceField(widget=forms.Select(attrs={
        'class': 'form-control select2',
        'style': 'width: 100%;'
    }), choices=())


class CashRegisterSessionOpenForm(ModelForm):
    """Apertura de caja: empresa, monto inicial y fecha/hora. Pasar user_open=request.user al instanciar."""

    def __init__(self, *args, **kwargs):
        self._user_open = kwargs.pop('user_open', None)
        super().__init__(*args, **kwargs)
        self.fields['opening_amount'].widget.attrs['autofocus'] = True
        if 'company' in self.fields:
            self.fields['company'].required = False
            self.fields['company'].widget.attrs.update({
                'class': 'form-control select2',
                'style': 'width: 100%;',
            })
        self.fields['opened_at'].input_formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
        if not self.data and not self.initial.get('opened_at'):
            self.initial['opened_at'] = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M')

    class Meta:
        model = CashRegisterSession
        fields = ['company', 'opening_amount', 'opened_at']
        widgets = {
            'opening_amount': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': '0.00',
            }),
            'opened_at': forms.DateTimeInput(
                format='%Y-%m-%d %H:%M',
                attrs={
                    'class': 'form-control',
                    'autocomplete': 'off',
                },
            ),
        }

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                if self._user_open is None:
                    data['error'] = 'No se indicó el usuario de apertura.'
                    return data
                self.instance.user_opened = self._user_open
                self.instance.status = CashRegisterSession.OPEN
                super().save(commit=commit)
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class CashRegisterSessionCloseForm(ModelForm):
    """Cierre de caja: montos, fecha/hora de cierre (formulario), diferencia y observaciones."""

    def __init__(self, *args, **kwargs):
        self._user_close = kwargs.pop('user_close', None)
        super().__init__(*args, **kwargs)
        self.fields['closing_amount_counted'].widget.attrs['autofocus'] = True
        self.fields['close_at'].required = True
        self.fields['close_at'].input_formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
        if not self.data and self.instance.close_at is None:
            self.initial['close_at'] = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M')

    class Meta:
        model = CashRegisterSession
        fields = [
            'closing_amount_counted',
            'closing_amount_expected',
            'difference_amount',
            'close_at',
            'observations',
        ]
        widgets = {
            'closing_amount_counted': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': '0.00',
            }),
            'closing_amount_expected': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': '0.00',
            }),
            'difference_amount': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': '0.00',
            }),
            'close_at': forms.DateTimeInput(
                format='%Y-%m-%d %H:%M',
                attrs={
                    'class': 'form-control',
                    'autocomplete': 'off',
                },
            ),
            'observations': forms.Textarea(attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'rows': 3,
                'cols': 3,
                'placeholder': 'Observaciones del cierre',
            }),
        }

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                if self._user_close is None:
                    data['error'] = 'No se indicó el usuario de cierre.'
                    return data
                self.instance.user_closed = self._user_close
                self.instance.status = CashRegisterSession.CLOSED
                super().save(commit=commit)
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data
