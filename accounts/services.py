from django.contrib.auth import login
from django.contrib.auth.models import Group

GROUP_TO_ROLE = {
    "Patient": "patient",
    "Doctor": "doctor",
    "Receptionist": "receptionist",
    "Admin": "admin",
}
ROLE_TO_GROUP = {v: k for k, v in GROUP_TO_ROLE.items()}


def get_user_role(instance):
    """Return role slug ('patient', 'doctor', …) based on the user's group."""
    for group in instance.groups.all():
        if group.name in GROUP_TO_ROLE:
            return GROUP_TO_ROLE[group.name]
    return None


def assign_group(instance, target_role):
    """Assign the matching auth Group to the user."""
    group_name = ROLE_TO_GROUP.get(target_role)
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        instance.groups.add(group)


def ensure_profile_for_role(instance, target_role):
    """Create the role-specific profile record if it doesn't already exist."""
    from accounts.models import (
        AdminProfile,
        DoctorProfile,
        PatientProfile,
        ReceptionistProfile,
    )

    if target_role == "patient" and not hasattr(instance, "patient_profile"):
        PatientProfile.objects.get_or_create(user=instance)
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
