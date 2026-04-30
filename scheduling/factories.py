from datetime import time, timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from accounts.factories import DoctorProfileFactory, UserFactory
from .models import AppointmentSlot, DoctorScheduleException, DoctorWeeklySchedule


class DoctorWeeklyScheduleFactory(DjangoModelFactory):
    class Meta:
        model = DoctorWeeklySchedule

    doctor = factory.SubFactory(DoctorProfileFactory)
    day_of_week = factory.Iterator([0, 1, 2, 3, 4])
    start_time = time(9, 0)
    end_time = time(17, 0)
    is_active = True


class DoctorScheduleExceptionFactory(DjangoModelFactory):
    class Meta:
        model = DoctorScheduleException

    doctor = factory.SubFactory(DoctorProfileFactory)
    exception_date = factory.Faker("future_date", end_date="+30d")
    type = factory.Iterator(
        [
            DoctorScheduleException.ExceptionType.DAY_OFF,
            DoctorScheduleException.ExceptionType.VACATION,
            DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY,
        ]
    )
    start_time = factory.LazyAttribute(
        lambda obj: time(10, 0)
        if obj.type == DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY
        else None
    )
    end_time = factory.LazyAttribute(
        lambda obj: time(14, 0)
        if obj.type == DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY
        else None
    )
    reason = factory.Faker("sentence", nb_words=6)
    created_by = factory.SubFactory(UserFactory)


class AppointmentSlotFactory(DjangoModelFactory):
    class Meta:
        model = AppointmentSlot

    doctor = factory.SubFactory(DoctorProfileFactory)
    start_datetime = factory.Sequence(
        lambda n: timezone.now().replace(second=0, microsecond=0)
        + timedelta(days=(n // 16), minutes=(n % 16) * 30)
    )
    end_datetime = factory.LazyAttribute(lambda obj: obj.start_datetime + timedelta(minutes=30))
    slot_date = factory.LazyAttribute(lambda obj: obj.start_datetime.date())
    status = AppointmentSlot.Status.AVAILABLE
    generated_from = AppointmentSlot.GeneratedFrom.WEEKLY_SCHEDULE
