from django.urls import path
from apps.scheduling.views import (
    AppointmentSlotViewSet, DoctorWeeklyScheduleViewSet, 
    DoctorScheduleExceptionViewSet, SlotGenerationViewSet
)

app_name = 'scheduling'

urlpatterns = [
    path('slots/', AppointmentSlotViewSet.as_view({'get': 'list', 'post': 'create'}), name='slot-list'),
    path('slots/<int:pk>/', AppointmentSlotViewSet.as_view({'get': 'retrieve'}), name='slot-detail'),
    path('weekly-schedules/', DoctorWeeklyScheduleViewSet.as_view({'get': 'list', 'post': 'create'}), name='weekly-schedule-list'),
    path('weekly-schedules/<int:pk>/', DoctorWeeklyScheduleViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='weekly-schedule-detail'),
    path('schedule-exceptions/', DoctorScheduleExceptionViewSet.as_view({'get': 'list', 'post': 'create'}), name='schedule-exception-list'),
    path('schedule-exceptions/<int:pk>/', DoctorScheduleExceptionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='schedule-exception-detail'),
]
