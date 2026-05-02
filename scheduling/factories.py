from datetime import time, timedelta
from random import choice, randint

from django.utils import timezone

from accounts.factories import DoctorProfileFactory
from scheduling.models import AppointmentSlot, DoctorScheduleException, DoctorWeeklySchedule


def DoctorWeeklyScheduleFactory(**kwargs):
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    day_of_week = kwargs.pop("day_of_week", randint(0, 6))
    start_hour = randint(8, 12)
    start_minute = choice([0, 30])
    duration_hours = randint(4, 8)
    start_time = kwargs.pop("start_time", time(start_hour, start_minute))
    end_hour = min(start_hour + duration_hours, 20)
    end_time = kwargs.pop("end_time", time(end_hour, start_minute))
    schedule, _ = DoctorWeeklySchedule.objects.get_or_create(
        doctor=doctor,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        defaults=kwargs,
    )
    return schedule


def DoctorScheduleExceptionFactory(**kwargs):
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    exception_type = kwargs.pop(
        "type",
        choice(
            [
                DoctorScheduleException.ExceptionType.DAY_OFF,
                DoctorScheduleException.ExceptionType.VACATION,
                DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY,
            ]
        ),
    )
    exception_date = kwargs.pop("exception_date", timezone.localdate() + timedelta(days=randint(-14, 30)))
    start_time = kwargs.pop("start_time", None)
    end_time = kwargs.pop("end_time", None)
    if exception_type == DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY:
        start_hour = randint(8, 12)
        start_minute = choice([0, 30])
        start_time = start_time or time(start_hour, start_minute)
        end_time = end_time or time(min(start_hour + randint(3, 6), 20), start_minute)
    reason = kwargs.pop(
        "reason",
        choice(
            [
                "Planned leave",
                "Personal commitment",
                "Holiday coverage",
                "Training session",
            ]
        ),
    )
    return DoctorScheduleException.objects.create(
        doctor=doctor,
        exception_date=exception_date,
        type=exception_type,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
        **kwargs,
    )


def AppointmentSlotFactory(**kwargs):
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    slot_date = kwargs.pop("slot_date", None)
    start = kwargs.pop("start_datetime", None)
    if start is None:
        start = timezone.now().replace(
            hour=randint(8, 16),
            minute=choice([0, 30]),
            second=0,
            microsecond=0,
        ) + timedelta(days=randint(-7, 21))
    end = kwargs.pop("end_datetime", None)
    if end is None:
        end = start + timedelta(minutes=choice([20, 30, 45]))
    if slot_date is None:
        slot_date = start.date()
    status = kwargs.pop("status", AppointmentSlot.Status.AVAILABLE)
    generated_from = kwargs.pop(
        "generated_from",
        AppointmentSlot.GeneratedFrom.WEEKLY_SCHEDULE,
    )
    return AppointmentSlot.objects.create(
        doctor=doctor,
        slot_date=slot_date,
        start_datetime=start,
        end_datetime=end,
        status=status,
        generated_from=generated_from,
        **kwargs,
    )
