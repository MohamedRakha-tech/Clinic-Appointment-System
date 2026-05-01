from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("read/<int:notification_id>/", views.NotificationMarkReadView.as_view(), name="mark_read"),
    path("read-all/", views.NotificationMarkAllReadView.as_view(), name="mark_all_read"),
]
