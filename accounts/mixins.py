from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    required_group = None

    def test_func(self):
        return self.request.user.groups.filter(name=self.required_group).exists()


class PatientRequiredMixin(RoleRequiredMixin):
    required_group = "Patient"


class DoctorRequiredMixin(RoleRequiredMixin):
    required_group = "Doctor"


class ReceptionistRequiredMixin(RoleRequiredMixin):
    required_group = "Receptionist"


class AdminRequiredMixin(RoleRequiredMixin):
    required_group = "Admin"
