# dashboard/urls.py

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',              views.DashboardRedirectView.as_view(),    name='home'),
    path('admin/',        views.AdminDashboardView.as_view(),        name='admin'),
    path('doctor/',       views.DoctorDashboardView.as_view(),       name='doctor'),
    path('receptionist/', views.ReceptionistDashboardView.as_view(), name='receptionist'),
    path('reports/',      views.ReportsView.as_view(),               name='reports'),

    path('export/appointments/', views.ExportAppointmentsView.as_view(), name='export-appointments'),
    path('export/noshow/',       views.ExportNoshowReportView.as_view(),  name='export-noshow'),
    path('export/revenue/',      views.ExportRevenueReportView.as_view(), name='export-revenue'),
    path('export/audit-log/',    views.ExportAuditLogView.as_view(),      name='export-audit-log'),
]