from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.AdminDashboardView.as_view(), name="index"),
    path("users/", views.UserManagementRedirectView.as_view(), name="users"),
]
