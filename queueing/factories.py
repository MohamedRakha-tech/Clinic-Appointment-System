from datetime import timedelta

import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from appointments.factories import AppointmentFactory
from appointments.models import Appointment
from .models import AppointmentCheckin


class AppointmentCheckinFactory(DjangoModelFactory):
    class Meta:
        model = AppointmentCheckin

    appointment = factory.SubFactory(AppointmentFactory, status=Appointment.Status.CHECKED_IN)
    checked_in_at = factory.LazyAttribute(lambda obj: obj.appointment.scheduled_start - timedelta(minutes=15))
    checked_in_by = factory.SubFactory(UserFactory)
    queue_number = factory.Sequence(lambda n: n + 1)
    called_at = None
    served_at = None
