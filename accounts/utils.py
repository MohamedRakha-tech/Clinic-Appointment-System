from django.contrib.auth.models import Group

ROLE_NAMES = ("patient", "doctor", "receptionist", "admin")


def ensure_role_groups():
    for name in ROLE_NAMES:
        Group.objects.get_or_create(name=name)


def get_user_role(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None

    if user.is_superuser:
        return "admin"

    for name in user.groups.values_list("name", flat=True):
        if name and name.lower() in ROLE_NAMES:
            return name.lower()

    if hasattr(user, "admin_profile"):
        return "admin"
    if hasattr(user, "doctor_profile"):
        return "doctor"
    if hasattr(user, "receptionist_profile"):
        return "receptionist"
    if hasattr(user, "patient_profile"):
        return "patient"

    return None


def set_user_role(user, role_name):
    if role_name not in ROLE_NAMES:
        raise ValueError("Invalid role name")

    ensure_role_groups()
    existing_roles = [group for group in user.groups.all() if group.name.lower() in ROLE_NAMES]
    if existing_roles:
        user.groups.remove(*existing_roles)
    user.groups.add(Group.objects.get(name=role_name))


def user_has_role(user, role_names):
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if user.is_superuser:
        return True

    role_names = {name.lower() for name in role_names}
    group_match = any(
        group.name and group.name.lower() in role_names
        for group in user.groups.all()
    )
    if group_match:
        return True

    profile_map = {
        "admin": "admin_profile",
        "doctor": "doctor_profile",
        "receptionist": "receptionist_profile",
        "patient": "patient_profile",
    }
    for role_name in role_names:
        profile_attr = profile_map.get(role_name)
        if profile_attr and hasattr(user, profile_attr):
            return True

    return False
