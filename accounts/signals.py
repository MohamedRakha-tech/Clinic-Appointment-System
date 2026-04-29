from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from accounts.services import GROUP_TO_ROLE, ROLE_TO_GROUP, assign_group, ensure_profile_for_role, get_user_role

User = get_user_model()

@receiver(post_save, sender=User)
def assign_role_and_create_profile(sender, instance, created, **kwargs):
    """
    Role/profile automation.
    - Patient register => _target_role='patient'
    - Admin-created staff => _target_role set in admin form
    - Fallback for new users => patient
    """
    target_role = getattr(instance, "_target_role", None)

    if not target_role:
        existing = get_user_role(instance)
        if existing:
            target_role = existing
        elif created:
            target_role = "patient"

    if not target_role or target_role not in ROLE_TO_GROUP:
        return

    assign_group(instance, target_role)
    ensure_profile_for_role(instance, target_role)
