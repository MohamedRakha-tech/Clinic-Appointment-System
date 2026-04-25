from django.urls import path
from apps.accounts.views import UserViewSet, PatientProfileViewSet, DoctorProfileViewSet

app_name = 'accounts'

urlpatterns = [
    path('users/', UserViewSet.as_view({'get': 'list', 'post': 'create'}), name='user-list'),
    path('users/<int:pk>/', UserViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='user-detail'),
    path('users/profile/', UserViewSet.as_view({'get': 'profile'}), name='user-profile'),
    path('patients/', PatientProfileViewSet.as_view({'get': 'list', 'post': 'create'}), name='patient-list'),
    path('patients/<int:pk>/', PatientProfileViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='patient-detail'),
    path('doctors/', DoctorProfileViewSet.as_view({'get': 'list', 'post': 'create'}), name='doctor-list'),
    path('doctors/<int:pk>/', DoctorProfileViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='doctor-detail'),
]
