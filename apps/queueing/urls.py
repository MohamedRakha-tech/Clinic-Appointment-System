from django.urls import path
from apps.queueing.views import QueueViewSet, CheckInViewSet

app_name = 'queueing'

urlpatterns = [
    path('queues/', QueueViewSet.as_view({'get': 'list'}), name='queue-list'),
    path('check-in/', CheckInViewSet.as_view({'post': 'create'}), name='check-in-create'),
]
