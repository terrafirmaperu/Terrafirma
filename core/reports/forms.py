from django import forms


class ReportForm(forms.Form):
    date_range = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off'
    }))

    sale = forms.ChoiceField(widget=forms.Select(attrs={
        'class': 'form-control select2',
        'style': 'width: 100%;'
    }))
