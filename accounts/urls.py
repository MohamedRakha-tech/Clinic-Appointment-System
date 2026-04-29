from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.register_view, name="signup"),
    path("patient/signup/", views.register_view, name="patient_signup"),
    path("login/", views.patient_login_view, name="login"),
    path("patient/login/", views.patient_login_view, name="patient_login"),
    path("staff/login/", views.staff_login_view, name="staff_login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/patient/", views.PatientDashboardView.as_view(), name="patient_dashboard"),
    path("dashboard/doctor/", views.DoctorDashboardView.as_view(), name="doctor_dashboard"),
    path("dashboard/reception/", views.ReceptionDashboardView.as_view(), name="reception_dashboard"),
    path("dashboard/admin/", views.AdminDashboardView.as_view(), name="admin_dashboard"),
]
