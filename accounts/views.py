from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from accounts.forms import LoginForm, PatientRegisterForm
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
                messages.error(request, "Please use the staff login portal.")
                return redirect("accounts:staff_login")
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
                messages.error(request, "Patients must use the patient login portal.")
                return redirect("accounts:patient_login")
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
