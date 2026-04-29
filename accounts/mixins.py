from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from accounts.utils import user_has_role


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    required_roles = []
    login_url = "/accounts/staff/login/"
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, self.required_roles)


class PatientRequiredMixin(RoleRequiredMixin):
    required_roles = ["patient"]
    login_url = "/accounts/patient/login/"


class DoctorRequiredMixin(RoleRequiredMixin):
    required_roles = ["doctor"]


class ReceptionistRequiredMixin(RoleRequiredMixin):
    required_roles = ["receptionist"]


class AdminRequiredMixin(RoleRequiredMixin):
    required_roles = ["admin"]
