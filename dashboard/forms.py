from django import forms
from django.contrib.auth.password_validation import validate_password

from accounts.models import AdminProfile, PatientProfile, ReceptionistProfile, User
from accounts.utils import ROLE_NAMES, ensure_role_groups, set_user_role


ROLE_CHOICES = [(name, name.title()) for name in ROLE_NAMES]


class UserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    employee_code = forms.CharField(required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "is_active":
                continue
            if not field.widget.attrs.get("class"):
                if isinstance(field, forms.ChoiceField):
                    field.widget.attrs["class"] = "form-select"
                else:
                    field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        employee_code = cleaned.get("employee_code")

        if role in {"receptionist", "admin"} and not employee_code:
            self.add_error("employee_code", "Employee code is required for this role.")

        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if password1:
            validate_password(password1)

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()

        role = self.cleaned_data["role"]
        ensure_role_groups()
        set_user_role(user, role)
        self._ensure_profile(user, role)

        return user

    def _ensure_profile(self, user, role):
        employee_code = self.cleaned_data.get("employee_code")

        if role == "patient":
            PatientProfile.objects.get_or_create(user=user)
        elif role == "receptionist":
            ReceptionistProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code},
            )
        elif role == "admin":
            AdminProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code},
            )


class UserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    employee_code = forms.CharField(required=False)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        self.original_role = kwargs.pop("original_role", None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "is_active":
                continue
            if not field.widget.attrs.get("class"):
                if isinstance(field, forms.ChoiceField):
                    field.widget.attrs["class"] = "form-select"
                else:
                    field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        employee_code = cleaned.get("employee_code")

        if role in {"receptionist", "admin"} and not employee_code:
            self.add_error("employee_code", "Employee code is required for this role.")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=commit)
        role = self.cleaned_data["role"]
        ensure_role_groups()
        set_user_role(user, role)
        self._ensure_profile(user, role)
        return user

    def _ensure_profile(self, user, role):
        employee_code = self.cleaned_data.get("employee_code")

        if role == "patient":
            PatientProfile.objects.get_or_create(user=user)
        elif role == "receptionist":
            ReceptionistProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code},
            )
        elif role == "admin":
            AdminProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code},
            )
