from django.db import models
from django.core.exceptions import ValidationError
from accounts.models import User, DoctorProfile
# ─────────────────────────────────────────────
# DOCTOR SCHEDULING
# ─────────────────────────────────────────────

class DoctorWeeklySchedule(models.Model):
    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    doctor      = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="weekly_schedules")
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "doctor_weekly_schedules"
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "day_of_week", "start_time", "end_time"],
                name="uniq_doctor_weekly_schedule",
            ),
            models.CheckConstraint(
                condition=models.Q(day_of_week__gte=0, day_of_week__lte=6),
                name="chk_day_of_week",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="chk_schedule_time",
            ),
        ]

    def clean(self):
        errors = {}

        if self.day_of_week is not None and not 0 <= self.day_of_week <= 6:
            errors["day_of_week"] = "Day of week must be between 0 and 6."

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["start_time"] = "Start time must be before end time."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class DoctorScheduleException(models.Model):
    class ExceptionType(models.TextChoices):
        DAY_OFF             = "DAY_OFF",             "Day Off"
        VACATION            = "VACATION",            "Vacation"
        SPECIAL_WORKING_DAY = "SPECIAL_WORKING_DAY", "Special Working Day"

    doctor         = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="schedule_exceptions")
    exception_date = models.DateField()
    type           = models.CharField(max_length=30, choices=ExceptionType.choices)
    start_time     = models.TimeField(blank=True, null=True)
    end_time       = models.TimeField(blank=True, null=True)
    reason         = models.CharField(max_length=255, blank=True, null=True)
    created_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_schedule_exceptions")
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "doctor_schedule_exceptions"

    def clean(self):
        errors = {}

        if self.type == self.ExceptionType.SPECIAL_WORKING_DAY:
            if not self.start_time:
                errors["start_time"] = "Start time is required for a special working day."
            if not self.end_time:
                errors["end_time"] = "End time is required for a special working day."

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["start_time"] = "Start time must be before end time."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.doctor} - {self.type} on {self.exception_date}"


# ─────────────────────────────────────────────
# APPOINTMENT SLOTS
# ─────────────────────────────────────────────

class AppointmentSlot(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        BOOKED    = "BOOKED",    "Booked"
        BLOCKED   = "BLOCKED",   "Blocked"
        EXPIRED   = "EXPIRED",   "Expired"

    class GeneratedFrom(models.TextChoices):
        WEEKLY_SCHEDULE = "WEEKLY_SCHEDULE", "Weekly Schedule"
        EXCEPTION       = "EXCEPTION",       "Exception"
        MANUAL          = "MANUAL",          "Manual"

    doctor         = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="slots")
    slot_date      = models.DateField()
    start_datetime = models.DateTimeField()
    end_datetime   = models.DateTimeField()
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    generated_from = models.CharField(max_length=20, choices=GeneratedFrom.choices, default=GeneratedFrom.WEEKLY_SCHEDULE)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointment_slots"
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start_datetime", "end_datetime"],
                name="uniq_doctor_slot",
            ),
            models.CheckConstraint(
                condition=models.Q(end_datetime__gt=models.F("start_datetime")),
                name="chk_slot_time",
            ),
        ]
        indexes = [
            models.Index(fields=["doctor", "slot_date", "status"], name="idx_slots_doctor_date_status"),
        ]

    def clean(self):
        if self.start_datetime and self.end_datetime and self.start_datetime >= self.end_datetime:
            raise ValidationError({"start_datetime": "Start datetime must be before end datetime."})

    def __str__(self):
        return f"{self.doctor} | {self.start_datetime} [{self.status}]"

