from django.contrib.auth import logout
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from accounts.forms import LoginForm, PatientRegisterForm
from accounts.mixins import AdminRequiredMixin, DoctorRequiredMixin, PatientRequiredMixin, ReceptionistRequiredMixin
from accounts.services import get_user_role, login_user


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
    return redirect("accounts:login")


@transaction.atomic
def register_view(request):
    """Public registration view (patients only)."""
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


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login_user(request, user)
            return _redirect_by_role(user)
    else:
        form = LoginForm(request)

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


class PatientDashboardView(PatientRequiredMixin, TemplateView):
    template_name = "accounts/patient_dashboard.html"


class DoctorDashboardView(DoctorRequiredMixin, TemplateView):
    template_name = "accounts/doctor_dashboard.html"


class ReceptionDashboardView(ReceptionistRequiredMixin, TemplateView):
    template_name = "accounts/receptionist_dashboard.html"


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = "accounts/admin_dashboard.html"
