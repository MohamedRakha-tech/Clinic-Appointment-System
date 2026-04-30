from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    # path("", views.AdminDashboardView.as_view(), name="index"),
    # path("users/", views.UserManagementRedirectView.as_view(), name="users"),
    path('',              views.DashboardRedirectView.as_view(),    name='home'),
    path('admin/',        views.AdminDashboardView.as_view(),        name='admin'),
    path('doctor/',       views.DoctorDashboardView.as_view(),       name='doctor'),
    path('receptionist/', views.ReceptionistDashboardView.as_view(), name='receptionist'),
    path('reports/',      views.ReportsView.as_view(),               name='reports'),

    path('export/appointments/', views.ExportAppointmentsView.as_view(), name='export-appointments'),
    path('export/noshow/',       views.ExportNoshowReportView.as_view(),  name='export-noshow'),
    path('export/revenue/',      views.ExportRevenueReportView.as_view(), name='export-revenue'),

    path("users/", views.UserListView.as_view(), name="users"),
    path("users/create/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_edit"),
    path("users/export/", views.export_users_csv, name="users_export"),

]