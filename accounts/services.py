from datetime import date

from django.contrib.auth import login

from accounts.utils import ROLE_NAMES, ensure_role_groups, set_user_role


DEFAULT_PATIENT_PROFILE_DATA = {
    "date_of_birth": date(1990, 1, 1),
    "gender": "Unknown",
    "address": "Not Provided",
}


def get_patient_profile_defaults(**overrides):
    defaults = DEFAULT_PATIENT_PROFILE_DATA.copy()
    defaults.update({key: value for key, value in overrides.items() if value not in (None, "")})
    return defaults


def assign_group(instance, target_role):
    """Assign the matching auth group to the user."""
    if target_role in ROLE_NAMES:
        ensure_role_groups()
        set_user_role(instance, target_role)


def ensure_profile_for_role(instance, target_role):
    """Create the role-specific profile record if it doesn't already exist."""
    from accounts.models import (
        AdminProfile,
        DoctorProfile,
        PatientProfile,
        ReceptionistProfile,
    )

    if target_role == "patient" and not hasattr(instance, "patient_profile"):
        PatientProfile.objects.get_or_create(
            user=instance,
            defaults=get_patient_profile_defaults(),
        )
    elif target_role == "doctor" and not hasattr(instance, "doctor_profile"):
        DoctorProfile.objects.get_or_create(
            user=instance,
            defaults={
                "specialization": "General",
                "license_number": f"DOC-{instance.id}",
            },
        )
    elif target_role == "receptionist" and not hasattr(instance, "receptionist_profile"):
        ReceptionistProfile.objects.get_or_create(
            user=instance,
            defaults={"employee_code": f"REC-{instance.id}"},
        )
    elif target_role == "admin" and not hasattr(instance, "admin_profile"):
        AdminProfile.objects.get_or_create(
            user=instance,
            defaults={"employee_code": f"ADM-{instance.id}"},
        )


def login_user(request, user):
    """
    Safely log in `user`, ensuring an auth backend is set.
    Prevents the 'multiple backends' ValueError when AUTHENTICATION_BACKENDS
    has more than one entry.
    """
    if not hasattr(user, "backend"):
        user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)
