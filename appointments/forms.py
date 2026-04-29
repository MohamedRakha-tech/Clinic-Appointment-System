from django import forms


class AppointmentBookingForm(forms.Form):
    doctor_id = forms.IntegerField(widget=forms.HiddenInput)
    slot_id = forms.IntegerField(widget=forms.HiddenInput)
    notes_for_staff = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "w-full bg-surface-container-high border border-outline-variant rounded-xl p-4 text-sm text-on-surface focus:ring-2 focus:ring-primary focus:border-transparent resize-none",
            "rows": 3,
            "placeholder": "Optional notes for staff...",
        }),
    )


class AppointmentActionForm(forms.Form):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "class": "w-full bg-surface-container-high border border-outline-variant rounded-xl p-4 text-sm text-on-surface focus:ring-2 focus:ring-primary focus:border-transparent resize-none",
            "rows": 4,
            "placeholder": "Add a brief reason...",
        }),
    )


class AppointmentRescheduleForm(forms.Form):
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            "class": "w-full bg-surface-container-high border border-outline-variant rounded-xl p-4 text-sm text-on-surface focus:ring-2 focus:ring-primary focus:border-transparent resize-none",
            "rows": 3,
            "placeholder": "Please provide a reason for rescheduling...",
        }),
    )
