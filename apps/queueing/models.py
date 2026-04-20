from django.db import models

from apps.accounts.models import User
from apps.appointments.models import Appointment

class AppointmentCheckin(models.Model):
    appointment     = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="checkin")
    checked_in_at   = models.DateTimeField()
    checked_in_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="checkins_performed")
    queue_number    = models.IntegerField(blank=True, null=True)
    called_at       = models.DateTimeField(blank=True, null=True)
    served_at       = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "appointment_checkins"

    def __str__(self):
        return f"Check-in for Appointment {self.appointment_id} at {self.checked_in_at}"

