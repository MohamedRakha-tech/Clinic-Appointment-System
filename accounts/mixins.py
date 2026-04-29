from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured, PermissionDenied


class ProfileRequiredMixin(LoginRequiredMixin):
    profile_attribute = None

    def get_profile(self):
        if not self.profile_attribute:
            raise ImproperlyConfigured("profile_attribute must be set")

        try:
            return getattr(self.request.user, self.profile_attribute)
        except AttributeError as exc:
            raise PermissionDenied from exc


class PatientProfileRequiredMixin(ProfileRequiredMixin):
    profile_attribute = "patient_profile"


class DoctorProfileRequiredMixin(ProfileRequiredMixin):
    profile_attribute = "doctor_profile"


class ReceptionistProfileRequiredMixin(ProfileRequiredMixin):
    profile_attribute = "receptionist_profile"


class ClinicStaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not self.is_clinic_staff(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def is_clinic_staff(user):
        if not user.is_authenticated:
            return False

        if user.is_superuser or user.is_staff:
            return True

        for attr in ("doctor_profile", "receptionist_profile", "admin_profile"):
            if hasattr(user, attr):
                return True

        return False


class AppointmentQuerysetMixin:
    def get_queryset(self):
        from appointments.filters import appointments_for_user

        return appointments_for_user(self.request.user)


class PatientAppointmentQuerysetMixin(AppointmentQuerysetMixin):
    def get_queryset(self):
        from appointments.filters import patient_appointments_for_user

        return patient_appointments_for_user(self.request.user)


class StaffAppointmentRequiredMixin(ClinicStaffRequiredMixin):
    pass
