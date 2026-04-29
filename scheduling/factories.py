from itertools import count

from django.utils import timezone

from accounts.factories import DoctorProfileFactory
from scheduling.models import AppointmentSlot, DoctorScheduleException, DoctorWeeklySchedule


_slot_seq = count(1)


def DoctorWeeklyScheduleFactory(**kwargs):
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    kwargs.setdefault("day_of_week", 0)
    kwargs.setdefault("start_time", timezone.datetime(2026, 1, 1, 9, 0).time())
    kwargs.setdefault("end_time", timezone.datetime(2026, 1, 1, 17, 0).time())
    return DoctorWeeklySchedule.objects.create(doctor=doctor, **kwargs)


def DoctorScheduleExceptionFactory(**kwargs):
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    kwargs.setdefault("exception_date", timezone.localdate())
    kwargs.setdefault("type", DoctorScheduleException.ExceptionType.DAY_OFF)
    return DoctorScheduleException.objects.create(doctor=doctor, **kwargs)


def AppointmentSlotFactory(**kwargs):
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    idx = next(_slot_seq)
    slot_date = kwargs.pop("slot_date", timezone.localdate())
    start = kwargs.pop("start_datetime", timezone.now() + timezone.timedelta(days=idx))
    end = kwargs.pop("end_datetime", start + timezone.timedelta(minutes=30))
    kwargs.setdefault("status", AppointmentSlot.Status.AVAILABLE)
    kwargs.setdefault("generated_from", AppointmentSlot.GeneratedFrom.MANUAL)
    return AppointmentSlot.objects.create(
        doctor=doctor,
        slot_date=slot_date,
        start_datetime=start,
        end_datetime=end,
        **kwargs,
    )
