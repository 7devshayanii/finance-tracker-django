"""
Forms for the Finance Tracking System.

Provides validated forms for creating/editing transactions
and for user registration.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Transaction


class TransactionForm(forms.ModelForm):
    """
    Form for creating and updating financial transactions.
    Validates that the amount is positive and all required fields are present.
    """

    class Meta:
        model = Transaction
        fields = ['amount', 'type', 'category', 'date', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter amount',
                'min': '0.01',
                'step': '0.01',
                'id': 'id_amount',
            }),
            'type': forms.Select(attrs={
                'class': 'form-input',
                'id': 'id_type',
            }),
            'category': forms.Select(attrs={
                'class': 'form-input',
                'id': 'id_category',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'id': 'id_date',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Add notes (optional)',
                'rows': 3,
                'id': 'id_description',
            }),
        }

    def clean_amount(self):
        """Ensure the amount is a positive value."""
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be a positive number.')
        return amount


class TransactionFilterForm(forms.Form):
    """
    Form for filtering the transaction list.
    All fields are optional — only provided values are used for filtering.
    """

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'id': 'id_date_from',
        }),
        label='From Date'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'id': 'id_date_to',
        }),
        label='To Date'
    )
    type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Transaction.TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'id': 'id_filter_type',
        }),
        label='Type'
    )
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + Transaction.CATEGORY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'id': 'id_filter_category',
        }),
        label='Category'
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search description...',
            'id': 'id_search',
        }),
        label='Search'
    )


class CustomUserCreationForm(UserCreationForm):
    """
    Extended user registration form that also captures email.
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email address',
            'id': 'id_email',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply consistent styling to all fields
        for field_name in ['username', 'password1', 'password2']:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-input',
                'id': f'id_{field_name}',
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
