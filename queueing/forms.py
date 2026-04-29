from django import forms
from .models import AppointmentCheckin


class CheckInForm(forms.Form):
    confirmation = forms.BooleanField(
        required=True,
        label="Confirm check-in",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
