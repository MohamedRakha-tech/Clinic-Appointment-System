from django.urls import path
from . import views

app_name = 'queueing'

urlpatterns = [
    path('check-in/<int:appointment_id>/', views.CheckInView.as_view(), name='checkin'),
    path('doctor/queue/', views.DoctorQueueView.as_view(), name='doctor_queue'),
    path('reception/monitor/', views.ReceptionQueueMonitorView.as_view(), name='reception_queue'),
]
