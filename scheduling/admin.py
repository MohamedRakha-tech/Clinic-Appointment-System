from django.contrib import admin

from scheduling.models import (
    AppointmentSlot,
    DoctorScheduleException,
    DoctorWeeklySchedule,
)


@admin.register(DoctorWeeklySchedule)
class DoctorWeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "day_of_week",
        "start_time",
        "end_time",
        "is_active",
        "updated_at",
    )
    list_filter = ("day_of_week", "is_active")
    search_fields = (
        "doctor__user__username",
        "doctor__user__first_name",
        "doctor__user__last_name",
        "doctor__specialization",
    )
    ordering = ("doctor", "day_of_week", "start_time")


@admin.register(DoctorScheduleException)
class DoctorScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "exception_date",
        "type",
        "start_time",
        "end_time",
        "created_by",
        "created_at",
    )
    list_filter = ("type", "exception_date")
    search_fields = (
        "doctor__user__username",
        "doctor__user__first_name",
        "doctor__user__last_name",
        "doctor__specialization",
        "reason",
    )
    ordering = ("-exception_date", "doctor")


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "slot_date",
        "start_datetime",
        "end_datetime",
        "status",
        "generated_from",
    )
    list_filter = ("status", "generated_from", "slot_date")
    search_fields = (
        "doctor__user__username",
        "doctor__user__first_name",
        "doctor__user__last_name",
        "doctor__specialization",
    )
    ordering = ("-slot_date", "doctor", "start_datetime")
