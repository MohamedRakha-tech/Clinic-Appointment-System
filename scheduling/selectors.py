from django.utils import timezone

from scheduling.models import AppointmentSlot


def get_available_slots(doctor=None, date=None):
    slots = AppointmentSlot.objects.filter(
        status=AppointmentSlot.Status.AVAILABLE,
        start_datetime__gt=timezone.now(),
    )

    if doctor is not None:
        slots = slots.filter(doctor=doctor)

    if date is not None:
        slots = slots.filter(slot_date=date)

    return slots.order_by("start_datetime")


def get_doctor_slots(doctor, date=None):
    slots = AppointmentSlot.objects.filter(doctor=doctor)

    if date is not None:
        slots = slots.filter(slot_date=date)

    return slots.order_by("start_datetime")


def get_slot_by_id(slot_id):
    return AppointmentSlot.objects.get(pk=slot_id)


def is_slot_available(slot):
    return (
        slot.status == AppointmentSlot.Status.AVAILABLE
        and slot.start_datetime > timezone.now()
    )


def get_slots_for_date(date):
    return AppointmentSlot.objects.filter(slot_date=date).order_by(
        "doctor",
        "start_datetime",
    )
