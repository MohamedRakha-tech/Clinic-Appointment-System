from datetime import timedelta
from random import choice, randint
from uuid import uuid4

from django.utils import timezone

from accounts.factories import DoctorProfileFactory, PatientProfileFactory, UserFactory
from appointments.models import Appointment, AppointmentCancellation, AppointmentRescheduleHistory, AppointmentStatusHistory
from scheduling.factories import AppointmentSlotFactory


def AppointmentFactory(**kwargs):
    patient = kwargs.pop("patient", None) or PatientProfileFactory()
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    status = kwargs.pop("status", Appointment.Status.REQUESTED)
    slot = kwargs.pop("slot", None)
    if slot is None:
        start_offset_days = randint(1, 21)
        if status in {Appointment.Status.CHECKED_IN, Appointment.Status.COMPLETED}:
            start_offset_days = -randint(0, 7)
        slot = AppointmentSlotFactory(
            doctor=doctor,
            start_datetime=timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
            + timedelta(days=start_offset_days),
        )
    appointment_code = kwargs.pop("appointment_code", f"APT-{uuid4().hex[:12].upper()}")
    kwargs.setdefault("status", status)
    kwargs.setdefault(
        "booking_source",
        choice(
            [
                Appointment.BookingSource.PATIENT,
                Appointment.BookingSource.RECEPTIONIST,
                Appointment.BookingSource.ADMIN,
            ]
        ),
    )
    kwargs.setdefault("scheduled_start", slot.start_datetime)
    kwargs.setdefault("scheduled_end", slot.end_datetime)
    appointment = Appointment.objects.create(
        appointment_code=appointment_code,
        patient=patient,
        doctor=doctor,
        slot=slot,
        **kwargs,
    )
    if appointment.status != Appointment.Status.CANCELLED:
        slot.status = "BOOKED"
        slot.save(update_fields=["status", "updated_at"])
    return appointment


def AppointmentStatusHistoryFactory(**kwargs):
    appointment = kwargs.pop("appointment", None) or AppointmentFactory(status=Appointment.Status.CONFIRMED)
    new_status = kwargs.pop("new_status", appointment.status)
    old_status = kwargs.pop(
        "old_status",
        Appointment.Status.REQUESTED if new_status != Appointment.Status.REQUESTED else Appointment.Status.CONFIRMED,
    )
    changed_by = kwargs.pop("changed_by", None) or UserFactory()
    kwargs.setdefault(
        "change_reason",
        choice(
            [
                "Initial status update",
                "Reception confirmation",
                "Patient arrived",
                "Administrative update",
            ]
        ),
    )
    return AppointmentStatusHistory.objects.create(
        appointment=appointment,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        **kwargs,
    )


def AppointmentRescheduleHistoryFactory(**kwargs):
    appointment = kwargs.pop("appointment", None) or AppointmentFactory(status=Appointment.Status.CONFIRMED)
    changed_by = kwargs.pop("changed_by", None) or UserFactory()
    old_start_datetime = kwargs.pop("old_start_datetime", appointment.scheduled_start)
    old_end_datetime = kwargs.pop("old_end_datetime", appointment.scheduled_end)
    duration = old_end_datetime - old_start_datetime if old_end_datetime > old_start_datetime else timedelta(minutes=30)
    new_start_datetime = kwargs.pop("new_start_datetime", old_start_datetime + timedelta(days=randint(1, 14)))
    new_end_datetime = kwargs.pop("new_end_datetime", new_start_datetime + duration)
    kwargs.setdefault(
        "reason",
        choice(
            [
                "Patient requested a new time",
                "Doctor availability changed",
                "Slot conflict resolved",
                "Administrative reschedule",
            ]
        ),
    )
    return AppointmentRescheduleHistory.objects.create(
        appointment=appointment,
        old_start_datetime=old_start_datetime,
        old_end_datetime=old_end_datetime,
        new_start_datetime=new_start_datetime,
        new_end_datetime=new_end_datetime,
        changed_by=changed_by,
        **kwargs,
    )


def AppointmentCancellationFactory(**kwargs):
    appointment = kwargs.pop("appointment", None) or AppointmentFactory(status=Appointment.Status.CANCELLED)
    cancelled_by = kwargs.pop("cancelled_by", None) or UserFactory()
    kwargs.setdefault(
        "reason",
        choice(
            [
                "Patient unavailable",
                "Doctor unavailable",
                "Administrative cancellation",
                "Appointment no longer needed",
            ]
        ),
    )
    appointment.status = Appointment.Status.CANCELLED
    appointment.cancelled_by = cancelled_by
    appointment.save(update_fields=["status", "cancelled_by", "updated_at"])
    return AppointmentCancellation.objects.create(
        appointment=appointment,
        cancelled_by=cancelled_by,
        **kwargs,
    )
