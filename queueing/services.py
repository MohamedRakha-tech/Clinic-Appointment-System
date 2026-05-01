from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from accounts.models import DoctorProfile
from appointments.models import Appointment
from appointments.services import transition_appointment
from .models import AppointmentCheckin


class QueueService:
    @staticmethod
    def _validate_check_in_window(appointment: Appointment, now):
        if appointment.scheduled_end <= appointment.scheduled_start:
            raise ValidationError("Appointment time range is invalid.")

        early_minutes = getattr(settings, "CHECKIN_EARLY_MINUTES", 60)
        late_minutes = getattr(settings, "CHECKIN_LATE_MINUTES", 120)

        start = timezone.localtime(appointment.scheduled_start)
        end = timezone.localtime(appointment.scheduled_end)
        earliest = start - timedelta(minutes=early_minutes)
        latest = end + timedelta(minutes=late_minutes)

        if now < earliest:
            raise ValidationError("Too early to check in for this appointment.")
        if now > latest:
            raise ValidationError("This appointment is too far past its time to check in.")

    @staticmethod
    @transaction.atomic
    def check_in_patient(appointment_id: int, checked_in_by) -> AppointmentCheckin:
        if not checked_in_by or not getattr(checked_in_by, "is_authenticated", False):
            raise ValidationError("Checked-in user is required.")

        appointment = (
            Appointment.objects.select_for_update()
            .select_related("doctor")
            .get(id=appointment_id)
        )

        if appointment.status != Appointment.Status.CONFIRMED:
            raise ValidationError("Only CONFIRMED appointments can be checked in.")

        if AppointmentCheckin.objects.select_for_update().filter(appointment=appointment).exists():
            raise ValidationError("Patient already checked in.")

        now = timezone.localtime(timezone.now())
        QueueService._validate_check_in_window(appointment, now)

        DoctorProfile.objects.select_for_update().get(pk=appointment.doctor_id)

        existing_checkins = AppointmentCheckin.objects.filter(
            appointment__doctor=appointment.doctor,
            appointment__scheduled_start__date=appointment.scheduled_start.date(),
        ).select_for_update()
        max_position = existing_checkins.aggregate(max_position=Max("queue_number")).get("max_position") or 0
        position = max_position + 1

        checkin = AppointmentCheckin.objects.create(
            appointment=appointment,
            checked_in_at=timezone.now(),
            checked_in_by=checked_in_by,
            queue_number=position,
        )

        transition_appointment(
            appointment,
            Appointment.Status.CHECKED_IN,
            changed_by=checked_in_by,
            reason="Patient checked in at reception",
        )

        return checkin
