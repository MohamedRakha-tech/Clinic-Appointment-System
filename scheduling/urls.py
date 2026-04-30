from django.urls import path

from scheduling import views

app_name = "scheduling"

urlpatterns = [
    path(
        "schedules/",
        views.WeeklyScheduleListView.as_view(),
        name="weekly_schedule_list",
    ),
    path(
        "schedules/create/",
        views.WeeklyScheduleCreateView.as_view(),
        name="weekly_schedule_create",
    ),
    path(
        "schedules/<int:pk>/edit/",
        views.WeeklyScheduleUpdateView.as_view(),
        name="weekly_schedule_update",
    ),
    path(
        "exceptions/",
        views.ScheduleExceptionListView.as_view(),
        name="schedule_exception_list",
    ),
    path(
        "exceptions/create/",
        views.ScheduleExceptionCreateView.as_view(),
        name="schedule_exception_create",
    ),
    path(
        "exceptions/<int:pk>/edit/",
        views.ScheduleExceptionUpdateView.as_view(),
        name="schedule_exception_update",
    ),
    path(
        "slots/",
        views.AppointmentSlotListView.as_view(),
        name="appointment_slot_list",
    ),
    path(
        "generate-slots/",
        views.GenerateSlotsView.as_view(),
        name="generate_slots",
    ),
    path(
        "generate/",
        views.GenerateSlotsView.as_view(),
        name="generate_slots_legacy",
    ),
    path(
        "my-schedule/",
        views.DoctorMyScheduleView.as_view(),
        name="doctor_my_schedule",
    ),
]
