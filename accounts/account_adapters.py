from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import resolve_url

from accounts.utils import get_user_role


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        provider = request.session.pop("social_login_provider", None)
        if provider == "google" and get_user_role(request.user) == "patient":
            return resolve_url("emr:patient_list")
        return super().get_login_redirect_url(request)
