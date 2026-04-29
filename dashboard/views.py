from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import RedirectView

from accounts.views import AdminDashboardView as AccountsAdminDashboardView


class AdminDashboardView(AccountsAdminDashboardView):
    """Expose the existing admin dashboard under the dashboard namespace."""


class UserManagementRedirectView(UserPassesTestMixin, RedirectView):
    pattern_name = "admin:accounts_user_changelist"
    permanent = False

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.is_superuser or hasattr(user, "admin_profile")
        )
