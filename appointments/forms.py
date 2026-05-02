from django import forms


class AppointmentBookingForm(forms.Form):
    doctor_id = forms.IntegerField(widget=forms.HiddenInput)
    slot_id = forms.IntegerField(widget=forms.HiddenInput)
    notes_for_staff = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Optional notes for staff...",
        }),
    )


class AppointmentActionForm(forms.Form):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Add a brief reason...",
        }),
    )


class AppointmentRescheduleForm(forms.Form):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Please provide a reason for rescheduling...",
        }),
    )
