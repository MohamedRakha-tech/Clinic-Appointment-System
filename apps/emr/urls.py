from django.urls import path
from apps.emr.views import ConsultationRecordViewSet

app_name = 'emr'

urlpatterns = [
    path('consultation-records/', ConsultationRecordViewSet.as_view({'get': 'list', 'post': 'create'}), name='consultation-record-list'),
    path('consultation-records/<int:pk>/', ConsultationRecordViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='consultation-record-detail'),
]
