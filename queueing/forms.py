from django import forms
from .models import AppointmentCheckin


class CheckInForm(forms.Form):
    """
    Simple form for confirming check-in.
    No model fields needed - just confirmation action.
    """
    confirmation = forms.BooleanField(
        required=True,
        label="Confirm check-in",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
