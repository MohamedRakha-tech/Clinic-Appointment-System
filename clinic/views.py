from django.shortcuts import render
from django.urls import reverse

from accounts.utils import get_user_role


def _get_error_home_context(request):
    role = get_user_role(getattr(request, "user", None))
    request_path = getattr(request, "path", "") or ""

    if request_path.startswith("/scheduling/"):
        if role in {"admin", "receptionist"}:
            return {
                "home_url": reverse("scheduling:weekly_schedule_list"),
                "home_label": "Back to Scheduling",
            }
        if role == "doctor":
            return {
                "home_url": reverse("scheduling:doctor_my_schedule"),
                "home_label": "Go to My Schedule",
            }

    role_home = {
        "admin": reverse("accounts:admin_dashboard"),
        "receptionist": reverse("accounts:reception_dashboard"),
        "doctor": reverse("accounts:doctor_dashboard"),
        "patient": reverse("accounts:patient_dashboard"),
    }
    return {
        "home_url": role_home.get(role, "/"),
        "home_label": "Go Home",
    }


def error_403(request, exception=None):
    return render(request, "403.html", _get_error_home_context(request), status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
