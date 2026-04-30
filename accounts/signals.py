from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver

from accounts.models import PatientProfile
from accounts.utils import set_user_role


def _ensure_patient_membership(user):
    set_user_role(user, "patient")
    PatientProfile.objects.get_or_create(user=user)


@receiver(user_signed_up)
def set_patient_role_on_social_signup(request, user, sociallogin=None, **kwargs):
    if sociallogin:
        _ensure_patient_membership(user)


@receiver(social_account_added)
def set_patient_role_on_social_account_added(request, sociallogin, **kwargs):
    _ensure_patient_membership(sociallogin.user)
