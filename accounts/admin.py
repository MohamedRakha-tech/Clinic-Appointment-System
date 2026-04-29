from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model

from accounts.models import AdminProfile, DoctorProfile, PatientProfile, ReceptionistProfile

User = get_user_model()


class UserAdminForm(forms.ModelForm):
    ROLE_CHOICES = (
        ("patient", "Patient"),
        ("doctor", "Doctor"),
        ("receptionist", "Receptionist"),
        ("admin", "Admin"),
    )

    role = forms.ChoiceField(choices=ROLE_CHOICES, required=False)
    raw_password = forms.CharField(required=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "is_active",
            "is_staff",
            "role",
            "raw_password",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("raw_password")
        if password:
            user.set_password(password)

        role = self.cleaned_data.get("role")
        if role in {"doctor", "receptionist", "admin"}:
            user.is_staff = True

        # Signal consumes this and creates group/profile automatically.
        user._target_role = role or None

        if commit:
            user.save()

        return user


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    list_display = ["id", "username", "email", "is_active", "is_staff"]
    search_fields = ["username", "email"]
    list_filter = ["is_active", "is_staff", "groups"]
    filter_horizontal = ["groups", "user_permissions"]


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "created_at"]
    search_fields = ["user__username", "user__email"]


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "specialization", "license_number"]
    search_fields = ["user__username", "license_number", "specialization"]


@admin.register(ReceptionistProfile)
class ReceptionistProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "employee_code"]
    search_fields = ["user__username", "employee_code"]


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "employee_code"]
    search_fields = ["user__username", "employee_code"]
