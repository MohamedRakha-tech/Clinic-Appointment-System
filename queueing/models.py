from django.db import models
from datetime import date

from accounts.models import User
from appointments.models import Appointment

def get_doctor_queue(doctor_id: int, target_date: date):
    return (
        AppointmentCheckin.objects
        .filter(
            appointment__doctor_id=doctor_id,
            appointment__scheduled_start__date=target_date,
            appointment__status='CHECKED_IN',
        )
        .select_related(
            'appointment',
            'appointment__patient',
            'appointment__patient__user'
        )
        .order_by('checked_in_at')
    )


def has_checkin_record(appointment_id: int) -> bool:
    return AppointmentCheckin.objects.filter(
        appointment_id=appointment_id
    ).exists()

class AppointmentCheckin(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="checkin")
    checked_in_at = models.DateTimeField()
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="checkins_performed")
    queue_number = models.IntegerField(blank=True, null=True)
    called_at = models.DateTimeField(blank=True, null=True)
    served_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "appointment_checkins"

    def __str__(self):
        return f"Check-in for Appointment {self.appointment_id} at {self.checked_in_at}"

