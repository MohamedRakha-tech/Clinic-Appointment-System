import uuid

from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils.text import slugify

from accounts.models import PatientProfile
from accounts.utils import get_user_role, set_user_role


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        if not user.username:
            email = data.get("email") or getattr(user, "email", "") or ""
            base = slugify(email.split("@")[0]) if email else ""
            base = base[:140] or "patient"
            user.username = f"{base}_{uuid.uuid4().hex[:8]}"

        return user

    def pre_social_login(self, request, sociallogin):
        email = (getattr(sociallogin.user, "email", "") or "").strip().lower()
        if not email:
            return

        User = get_user_model()
        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        role = get_user_role(existing_user)
        if role and role != "patient":
            raise ImmediateHttpResponse(
                redirect("/accounts/patient/login/?error=not_patient")
            )

        if not sociallogin.is_existing:
            sociallogin.connect(request, existing_user)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        set_user_role(user, "patient")
        PatientProfile.objects.get_or_create(user=user)
        return user
