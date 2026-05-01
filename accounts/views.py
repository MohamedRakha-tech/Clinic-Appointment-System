from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from accounts.forms import (AdminProfileForm, DoctorProfileForm, LoginForm,
                            PatientProfileForm, PatientRegisterForm,
                            ReceptionistProfileForm)
from accounts.mixins import AdminRequiredMixin, DoctorRequiredMixin, PatientRequiredMixin, ReceptionistRequiredMixin
from accounts.services import login_user
from accounts.utils import get_user_role


def _redirect_by_role(user):
    role = get_user_role(user)
    if role == "patient":
        return redirect("accounts:patient_dashboard")
    if role == "doctor":
        return redirect("accounts:doctor_dashboard")
    if role == "receptionist":
        return redirect("accounts:reception_dashboard")
    if role == "admin":
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:patient_login")


def _redirect_if_authenticated(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    return None


@transaction.atomic
def register_view(request):
    """Public registration view (patients only)."""
    redirect_response = _redirect_if_authenticated(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = PatientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Signal will assign Patient group and create PatientProfile.
            user._target_role = "patient"
            user.save()
            # Persist the profile-specific fields (date_of_birth, gender, address).
            form.save_profile(user)
            login_user(request, user)
            return redirect("accounts:patient_dashboard")
    else:
        form = PatientRegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def patient_login_view(request):
    redirect_response = _redirect_if_authenticated(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if get_user_role(user) != "patient":
                form.add_error(None, "Please use the staff login portal.")
                return render(request, "accounts/login.html", {"form": form, "is_staff_login": False})
            login_user(request, user)
            return _redirect_by_role(user)
    else:
        form = LoginForm(request)

    return render(request, "accounts/login.html", {"form": form, "is_staff_login": False})


def staff_login_view(request):
    redirect_response = _redirect_if_authenticated(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if get_user_role(user) == "patient":
                form.add_error(None, "Patients must use the patient login portal.")
                return render(request, "accounts/login.html", {"form": form, "is_staff_login": True})
            login_user(request, user)
            return _redirect_by_role(user)
    else:
        form = LoginForm(request)

    return render(request, "accounts/login.html", {"form": form, "is_staff_login": True})


def logout_view(request):
    role = get_user_role(request.user)
    logout(request)
    if role == "patient":
        return redirect("accounts:patient_login")
    return redirect("accounts:staff_login")


class PatientDashboardView(PatientRequiredMixin, TemplateView):
    template_name = "accounts/patient_dashboard.html"


class DoctorDashboardView(DoctorRequiredMixin, TemplateView):
    template_name = "accounts/doctor_dashboard.html"


class ReceptionDashboardView(ReceptionistRequiredMixin, TemplateView):
    template_name = "accounts/receptionist_dashboard.html"


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = "accounts/admin_dashboard.html"


# ─────────────────────────────────────────────
# PROFILES
# ─────────────────────────────────────────────

class PatientProfileView(PatientRequiredMixin, TemplateView):
    template_name = "patients/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = getattr(self.request.user, 'patient_profile', None)
        return context


class PatientProfileEditView(PatientRequiredMixin, UpdateView):
    template_name = "patients/profile_edit.html"
    form_class = PatientProfileForm
    success_url = reverse_lazy("accounts:patient_profile")

    def get_object(self, queryset=None):
        return self.request.user


class DoctorProfileView(DoctorRequiredMixin, TemplateView):
    template_name = "doctors/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor'] = getattr(self.request.user, 'doctor_profile', None)
        return context


class DoctorProfileEditView(DoctorRequiredMixin, UpdateView):
    template_name = "doctors/profile_edit.html"
    form_class = DoctorProfileForm
    success_url = reverse_lazy("accounts:doctor_profile")

    def get_object(self, queryset=None):
        return self.request.user


class ReceptionistProfileView(ReceptionistRequiredMixin, TemplateView):
    template_name = "receptionists/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['receptionist'] = getattr(self.request.user, 'receptionist_profile', None)
        return context


class ReceptionistProfileEditView(ReceptionistRequiredMixin, UpdateView):
    template_name = "receptionists/profile_edit.html"
    form_class = ReceptionistProfileForm
    success_url = reverse_lazy("accounts:reception_profile")

    def get_object(self, queryset=None):
        return self.request.user


class AdminProfileView(AdminRequiredMixin, TemplateView):
    template_name = "admins/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_user'] = getattr(self.request.user, 'admin_profile', None)
        return context


class AdminProfileEditView(AdminRequiredMixin, UpdateView):
    template_name = "admins/profile_edit.html"
    form_class = AdminProfileForm
    success_url = reverse_lazy("accounts:admin_profile")

    def get_object(self, queryset=None):
        return self.request.user
class PrivacyPolicyView(TemplateView):
    template_name = "accounts/info_page.html"
    page_title = "Privacy Policy"
    page_heading = "Privacy Policy"
    page_intro = "We only use your data to provide care, schedule appointments, and secure the portal."
    page_points = [
        "Medical data stays tied to your clinical record and authenticated account.",
        "We do not expose another patient's appointment or medical history to you.",
        "Shared demo accounts are only for local development and testing.",
    ]


class TermsOfServiceView(TemplateView):
    template_name = "accounts/info_page.html"
    page_title = "Terms of Service"
    page_heading = "Terms of Service"
    page_intro = "These demo terms explain how the clinic portal is intended to be used during development."
    page_points = [
        "Use the portal only for legitimate clinic workflows and testing.",
        "Patients can book their own appointments, not someone else's.",
        "Staff actions are limited by role-based permissions and server-side checks.",
    ]


class SupportView(TemplateView):
    template_name = "accounts/info_page.html"
    page_title = "Contact Support"
    page_heading = "Contact Support"
    page_intro = "If login, booking, or permissions are not behaving as expected, use the options below."
    page_points = [
        "Patient login: /accounts/patient/login/",
        "Staff login: /accounts/staff/login/",
        "For local demo issues, ask the team maintaining the seeder and slot fixtures.",
    ]
