from django import forms

from bufia.models import Refund


class RefundForm(forms.ModelForm):
    class Meta:
        model = Refund
        fields = ['amount', 'method', 'reason']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Enter refund amount',
            }),
            'method': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a short reason for this refund',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.payment = kwargs.pop('payment', None)
        super().__init__(*args, **kwargs)

        if self.payment:
            self.instance.payment = self.payment
            self.fields['method'].initial = self._default_method_for_payment()

    def _default_method_for_payment(self) -> str:
        if self.payment.amount_received is not None:
            return 'cash'
        if self.payment.payment_channel_display == 'Gcash Payment':
            return 'gcash'
        if self.payment.payment_provider == 'manual':
            return 'manual'
        return 'bank_transfer'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount is None:
            raise forms.ValidationError('Refund amount is required.')
        if amount <= 0:
            raise forms.ValidationError('Refund amount must be greater than 0.')
        if self.payment and amount > self.payment.refundable_balance:
            raise forms.ValidationError(
                f"Refund amount cannot exceed refundable balance of PHP {self.payment.refundable_balance:.2f}."
            )

        return amount
