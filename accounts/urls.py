from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.register_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/patient/", views.PatientDashboardView.as_view(), name="patient_dashboard"),
    path("dashboard/doctor/", views.DoctorDashboardView.as_view(), name="doctor_dashboard"),
    path("dashboard/reception/", views.ReceptionDashboardView.as_view(), name="reception_dashboard"),
    path("dashboard/admin/", views.AdminDashboardView.as_view(), name="admin_dashboard"),

    # Profiles
    path("profile/patient/", views.PatientProfileView.as_view(), name="patient_profile"),
    path("profile/patient/edit/", views.PatientProfileEditView.as_view(), name="patient_profile_edit"),
    
    path("profile/doctor/", views.DoctorProfileView.as_view(), name="doctor_profile"),
    path("profile/doctor/edit/", views.DoctorProfileEditView.as_view(), name="doctor_profile_edit"),
    
    path("profile/reception/", views.ReceptionistProfileView.as_view(), name="reception_profile"),
    path("profile/reception/edit/", views.ReceptionistProfileEditView.as_view(), name="reception_profile_edit"),
    
    path("profile/admin/", views.AdminProfileView.as_view(), name="admin_profile"),
    path("profile/admin/edit/", views.AdminProfileEditView.as_view(), name="admin_profile_edit"),
]
