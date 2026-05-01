from datetime import timedelta
from random import randint

from django.utils import timezone

from accounts.factories import UserFactory
from appointments.factories import AppointmentFactory
from queueing.models import AppointmentCheckin


def AppointmentCheckinFactory(**kwargs):
    appointment = kwargs.pop("appointment", None) or AppointmentFactory(status="CHECKED_IN")
    checked_in_by = kwargs.pop("checked_in_by", None) or UserFactory()
    kwargs.setdefault("checked_in_at", timezone.now() - timedelta(minutes=randint(0, 360)))
    kwargs.setdefault("queue_number", randint(1, 20))
    appointment.status = "CHECKED_IN"
    appointment.save(update_fields=["status", "updated_at"])
    return AppointmentCheckin.objects.create(
        appointment=appointment,
        checked_in_by=checked_in_by,
        **kwargs,
    )
