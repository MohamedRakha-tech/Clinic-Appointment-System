from django import forms
from django.contrib.auth.password_validation import validate_password

from accounts.models import AdminProfile, DoctorProfile, PatientProfile, ReceptionistProfile, User
from accounts.utils import ROLE_NAMES, ensure_role_groups, set_user_role


ROLE_CHOICES = [(name, name.title()) for name in ROLE_NAMES]


class UserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    
    # Role specific fields
    employee_code = forms.CharField(required=False)
    specialization = forms.CharField(required=False)
    license_number = forms.CharField(required=False)
    consultation_fee = forms.DecimalField(max_digits=8, decimal_places=2, required=False, initial=150.00)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=[('', '---------'), ('M', 'Male'), ('F', 'Female')], required=False)

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
            
        if role == "doctor":
            if not cleaned.get("specialization"):
                self.add_error("specialization", "Specialization is required for doctors.")
            if not cleaned.get("license_number"):
                self.add_error("license_number", "License number is required for doctors.")
            if cleaned.get("consultation_fee") is None:
                self.add_error("consultation_fee", "Consultation fee is required for doctors.")

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
        specialization = self.cleaned_data.get("specialization")
        license_number = self.cleaned_data.get("license_number")
        consultation_fee = self.cleaned_data.get("consultation_fee")
        date_of_birth = self.cleaned_data.get("date_of_birth")
        gender = self.cleaned_data.get("gender")

        if role == "patient":
            profile, _ = PatientProfile.objects.get_or_create(user=user)
            if date_of_birth:
                profile.date_of_birth = date_of_birth
            if gender:
                profile.gender = gender
            profile.save()
        elif role == "doctor":
            profile, _ = DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "specialization": specialization or "General",
                    "license_number": license_number or "PENDING",
                    "consultation_fee": consultation_fee or 150.00
                }
            )
            if specialization: profile.specialization = specialization
            if license_number: profile.license_number = license_number
            if consultation_fee is not None: profile.consultation_fee = consultation_fee
            profile.save()
        elif role == "receptionist":
            profile, _ = ReceptionistProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code or "TEMP"},
            )
            if employee_code:
                profile.employee_code = employee_code
                profile.save()
        elif role == "admin":
            profile, _ = AdminProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code or "TEMP"},
            )
            if employee_code:
                profile.employee_code = employee_code
                profile.save()


class UserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    
    # Role specific fields
    employee_code = forms.CharField(required=False)
    specialization = forms.CharField(required=False)
    license_number = forms.CharField(required=False)
    consultation_fee = forms.DecimalField(max_digits=8, decimal_places=2, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=[('', '---------'), ('M', 'Male'), ('F', 'Female')], required=False)

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
            
        if role == "doctor":
            if not cleaned.get("specialization"):
                self.add_error("specialization", "Specialization is required for doctors.")
            if not cleaned.get("license_number"):
                self.add_error("license_number", "License number is required for doctors.")
            if cleaned.get("consultation_fee") is None:
                self.add_error("consultation_fee", "Consultation fee is required for doctors.")

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
        specialization = self.cleaned_data.get("specialization")
        license_number = self.cleaned_data.get("license_number")
        consultation_fee = self.cleaned_data.get("consultation_fee")
        date_of_birth = self.cleaned_data.get("date_of_birth")
        gender = self.cleaned_data.get("gender")

        if role == "patient":
            profile, _ = PatientProfile.objects.get_or_create(user=user)
            if date_of_birth:
                profile.date_of_birth = date_of_birth
            if gender:
                profile.gender = gender
            profile.save()
        elif role == "doctor":
            profile, _ = DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "specialization": specialization or "General",
                    "license_number": license_number or "PENDING",
                    "consultation_fee": consultation_fee or 150.00
                }
            )
            if specialization: profile.specialization = specialization
            if license_number: profile.license_number = license_number
            if consultation_fee is not None: profile.consultation_fee = consultation_fee
            profile.save()
        elif role == "receptionist":
            profile, _ = ReceptionistProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code or "TEMP"},
            )
            if employee_code:
                profile.employee_code = employee_code
                profile.save()
        elif role == "admin":
            profile, _ = AdminProfile.objects.get_or_create(
                user=user,
                defaults={"employee_code": employee_code or "TEMP"},
            )
            if employee_code:
                profile.employee_code = employee_code
                profile.save()
