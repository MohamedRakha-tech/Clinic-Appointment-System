from django.db import models
from accounts.models import User, PatientProfile, DoctorProfile
from scheduling.models import AppointmentSlot

# ─────────────────────────────────────────────
# APPOINTMENTS
# ─────────────────────────────────────────────

class Appointment(models.Model):
    class Status(models.TextChoices):
        REQUESTED  = "REQUESTED",  "Requested"
        CONFIRMED  = "CONFIRMED",  "Confirmed"
        CHECKED_IN = "CHECKED_IN", "Checked In"
        COMPLETED  = "COMPLETED",  "Completed"
        CANCELLED  = "CANCELLED",  "Cancelled"
        NO_SHOW    = "NO_SHOW",    "No Show"

    class BookingSource(models.TextChoices):
        PATIENT      = "PATIENT",      "Patient"
        RECEPTIONIST = "RECEPTIONIST", "Receptionist"
        ADMIN        = "ADMIN",        "Admin"

    appointment_code    = models.CharField(max_length=20, unique=True)
    patient             = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="appointments")
    doctor              = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    slot                = models.ForeignKey(AppointmentSlot, on_delete=models.RESTRICT, related_name="appointments")
    scheduled_start     = models.DateTimeField()
    scheduled_end       = models.DateTimeField()
    status              = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    booking_source      = models.CharField(max_length=20, choices=BookingSource.choices, default=BookingSource.PATIENT)
    confirmed_by        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="confirmed_appointments")
    checked_in_by       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="checked_in_appointments")
    cancelled_by        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="cancelled_appointments")
    cancellation_reason = models.CharField(max_length=255, blank=True, null=True)
    notes_for_staff     = models.TextField(blank=True, null=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointments"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(scheduled_end__gt=models.F("scheduled_start")),
                name="chk_appointment_time",
            ),
        ]
        indexes = [
            models.Index(fields=["patient", "scheduled_start"], name="idx_appointments_patient_start"),
            models.Index(fields=["doctor", "scheduled_start"],  name="idx_appointments_doctor_start"),
            models.Index(fields=["status"],                     name="idx_appointments_status"),
        ]

    def __str__(self):
        return f"{self.appointment_code} | {self.patient} -> {self.doctor} [{self.status}]"

    @property
    def was_rescheduled(self):
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "reschedule_history" in prefetched:
            return bool(prefetched["reschedule_history"])
        return self.reschedule_history.exists()

    @property
    def display_status(self):
        if self.status == self.Status.REQUESTED and self.was_rescheduled:
            return "Rescheduled"
        return self.get_status_display()


# ─────────────────────────────────────────────
# AUDIT / HISTORY TABLES
# ─────────────────────────────────────────────

class AppointmentStatusHistory(models.Model):
    appointment   = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="status_history")
    old_status    = models.CharField(max_length=20, blank=True, null=True)
    new_status    = models.CharField(max_length=20)
    changed_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointment_status_changes")
    change_reason = models.CharField(max_length=255, blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "appointment_status_history"
        indexes  = [
            models.Index(fields=["appointment"], name="idx_status_history_appointment"),
        ]

    def __str__(self):
        return f"Appointment {self.appointment_id}: {self.old_status} -> {self.new_status}"


class AppointmentRescheduleHistory(models.Model):
    appointment        = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="reschedule_history")
    old_start_datetime = models.DateTimeField()
    old_end_datetime   = models.DateTimeField()
    new_start_datetime = models.DateTimeField()
    new_end_datetime   = models.DateTimeField()
    changed_by         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointment_reschedules")
    reason             = models.CharField(max_length=255)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "appointment_reschedule_history"
        indexes  = [
            models.Index(fields=["appointment"], name="idx_resched_hist_appt"),
        ]

    def __str__(self):
        return f"Reschedule for Appointment {self.appointment_id}"


class AppointmentCancellation(models.Model):
    appointment   = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="cancellations")
    cancelled_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointment_cancellations")
    reason        = models.CharField(max_length=255)
    cancelled_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "appointment_cancellations"

    def __str__(self):
        return f"Cancellation for Appointment {self.appointment_id}"


