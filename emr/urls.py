from django.urls import path
from . import views

app_name = 'emr'

urlpatterns = [
    path('consultations/', views.ConsultationListView.as_view(), name='list'),
    path('consultations/reception/', views.ReceptionConsultationListView.as_view(), name='reception_list'),
    path('patient/consultations/', views.PatientConsultationListView.as_view(), name='patient_list'),
    path('consultations/<int:pk>/', views.ConsultationDetailView.as_view(), name='detail'),
    path('consultations/create/<int:appointment_id>/', views.ConsultationCreateView.as_view(), name='create'),
    path('consultations/<int:pk>/edit/', views.ConsultationUpdateView.as_view(), name='edit'),
    path('consultations/<int:pk>/delete/', views.ConsultationDeleteView.as_view(), name='delete'),
]
