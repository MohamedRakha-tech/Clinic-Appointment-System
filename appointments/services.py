from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from accounts.models import PatientProfile
from appointments.models import (
    Appointment,
    AppointmentCancellation,
    AppointmentRescheduleHistory,
    AppointmentStatusHistory,
)
from scheduling.models import AppointmentSlot


def _generate_temporary_code():
    return f"TEMP-{uuid4().hex[:14].upper()}"


def _finalize_appointment_code(appointment):
    appointment.appointment_code = f"APT-{appointment.pk:08d}"
    appointment.save(update_fields=["appointment_code", "updated_at"])


def _booking_source_for_user(user):
    if hasattr(user, "patient_profile"):
        return Appointment.BookingSource.PATIENT
    if hasattr(user, "receptionist_profile"):
        return Appointment.BookingSource.RECEPTIONIST
    return Appointment.BookingSource.ADMIN


def _active_appointment_queryset(exclude_appointment_id=None):
    queryset = Appointment.objects.filter(
        status__in={
            Appointment.Status.REQUESTED,
            Appointment.Status.CONFIRMED,
            Appointment.Status.CHECKED_IN,
        }
    ).select_related("doctor", "doctor__user", "patient", "patient__user")

    if exclude_appointment_id:
        queryset = queryset.exclude(pk=exclude_appointment_id)

    return queryset


def _patient_has_overlapping_appointment(patient: PatientProfile, start, end, exclude_appointment_id=None) -> bool:
    return _active_appointment_queryset(exclude_appointment_id).filter(
        patient=patient,
        scheduled_start__lt=end,
        scheduled_end__gt=start,
    ).exists()


def _doctor_has_buffer_conflict(doctor, start, end, exclude_appointment_id=None) -> bool:
    buffer_before = getattr(doctor, "buffer_before_minutes", 5) or 0
    buffer_after = getattr(doctor, "buffer_after_minutes", 5) or 0
    conflict_start = start - timedelta(minutes=buffer_before)
    conflict_end = end + timedelta(minutes=buffer_after)

    return _active_appointment_queryset(exclude_appointment_id).filter(
        doctor=doctor,
        scheduled_start__lt=conflict_end,
        scheduled_end__gt=conflict_start,
    ).exists()


def _validate_booking_window(patient: PatientProfile, doctor, start, end, exclude_appointment_id=None):
    errors = []

    if _patient_has_overlapping_appointment(patient, start, end, exclude_appointment_id=exclude_appointment_id):
        errors.append("You already have another appointment that overlaps with this time.")

    if _doctor_has_buffer_conflict(doctor, start, end, exclude_appointment_id=exclude_appointment_id):
        errors.append("This time conflicts with the doctor's existing appointments or buffer window.")

    if errors:
        raise ValidationError(errors)


@transaction.atomic
def book_appointment(patient: PatientProfile, slot_id: int, booked_by=None, notes_for_staff: str = "") -> Appointment:
    slot = AppointmentSlot.objects.select_for_update().select_related("doctor", "doctor__user").get(pk=slot_id)

    if slot.status != AppointmentSlot.Status.AVAILABLE:
        raise ValidationError("This slot is no longer available.")

    if hasattr(slot, "appointment"):
        raise ValidationError("This slot has already been booked.")

    _validate_booking_window(patient, slot.doctor, slot.start_datetime, slot.end_datetime)

    appointment = Appointment.objects.create(
        appointment_code=_generate_temporary_code(),
        patient=patient,
        doctor=slot.doctor,
        slot=slot,
        scheduled_start=slot.start_datetime,
        scheduled_end=slot.end_datetime,
        status=Appointment.Status.REQUESTED,
        booking_source=_booking_source_for_user(booked_by or patient.user),
        notes_for_staff=notes_for_staff or None,
    )

    slot.status = AppointmentSlot.Status.BOOKED
    slot.save(update_fields=["status", "updated_at"])

    AppointmentStatusHistory.objects.create(
        appointment=appointment,
        old_status=None,
        new_status=Appointment.Status.REQUESTED,
        changed_by=booked_by,
        change_reason="Appointment booked",
    )

    _finalize_appointment_code(appointment)
    return appointment


@transaction.atomic
def transition_appointment(appointment_or_id, new_status: str, changed_by=None, reason: str = "") -> Appointment:
    appointment_id = getattr(appointment_or_id, "pk", appointment_or_id)
    appointment = (
        Appointment.objects.select_for_update()
        .select_related("slot", "patient", "doctor")
        .get(pk=appointment_id)
    )

    old_status = appointment.status
    if old_status == new_status:
        return appointment

    allowed = {
        Appointment.Status.REQUESTED: {
            Appointment.Status.CONFIRMED,
            Appointment.Status.CANCELLED,
            Appointment.Status.NO_SHOW,
        },
        Appointment.Status.CONFIRMED: {
            Appointment.Status.CHECKED_IN,
            Appointment.Status.CANCELLED,
            Appointment.Status.NO_SHOW,
            Appointment.Status.REQUESTED,
        },
        Appointment.Status.CHECKED_IN: {Appointment.Status.COMPLETED},
        Appointment.Status.NO_SHOW: set(),
        Appointment.Status.CANCELLED: set(),
        Appointment.Status.COMPLETED: set(),
    }
    if new_status not in allowed.get(old_status, set()):
        raise ValidationError(f"Cannot transition from {old_status} to {new_status}.")

    if new_status == Appointment.Status.COMPLETED and not hasattr(appointment, "consultation_record"):
        raise ValidationError("A consultation record must exist before completing the appointment.")

    appointment.status = new_status

    if new_status == Appointment.Status.CONFIRMED:
        appointment.confirmed_by = changed_by
    elif new_status == Appointment.Status.CHECKED_IN:
        appointment.checked_in_by = changed_by
    elif new_status == Appointment.Status.CANCELLED:
        appointment.cancelled_by = changed_by
        appointment.cancellation_reason = reason or appointment.cancellation_reason
        if appointment.slot_id:
            locked_slot = AppointmentSlot.objects.select_for_update().get(pk=appointment.slot_id)
            if locked_slot.status != AppointmentSlot.Status.AVAILABLE:
                locked_slot.status = AppointmentSlot.Status.AVAILABLE
                locked_slot.save(update_fields=["status", "updated_at"])

    appointment.save(
        update_fields=[
            "status",
            "confirmed_by",
            "checked_in_by",
            "cancelled_by",
            "cancellation_reason",
            "updated_at",
        ]
    )

    AppointmentStatusHistory.objects.create(
        appointment=appointment,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        change_reason=reason or None,
    )
    return appointment


@transaction.atomic
def cancel_appointment(appointment_or_id, cancelled_by=None, reason: str = "") -> Appointment:
    appointment = transition_appointment(appointment_or_id, Appointment.Status.CANCELLED, changed_by=cancelled_by, reason=reason)
    AppointmentCancellation.objects.create(
        appointment=appointment,
        cancelled_by=cancelled_by,
        reason=reason,
    )
    return appointment


@transaction.atomic
def reschedule_appointment(appointment_or_id, new_slot_id: int, changed_by=None, reason: str = "") -> Appointment:
    appointment_id = getattr(appointment_or_id, "pk", appointment_or_id)
    appointment = (
        Appointment.objects.select_for_update()
        .select_related("slot", "doctor", "patient")
        .get(pk=appointment_id)
    )

    if appointment.status in {Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW}:
        raise ValidationError("This appointment cannot be rescheduled.")

    if appointment.slot_id == new_slot_id:
        raise ValidationError("Please choose a different slot.")

    slot_ids = sorted({appointment.slot_id, new_slot_id})
    locked_slots = {
        slot.id: slot
        for slot in AppointmentSlot.objects.select_for_update()
        .filter(id__in=slot_ids)
        .order_by("id")
        .select_related("doctor", "doctor__user")
    }
    old_slot = locked_slots[appointment.slot_id]
    new_slot = locked_slots.get(new_slot_id)
    if new_slot is None:
        raise ValidationError("Selected slot was not found.")

    if new_slot.doctor_id != appointment.doctor_id:
        raise ValidationError("You can only reschedule within the same doctor's availability.")

    if new_slot.status != AppointmentSlot.Status.AVAILABLE:
        raise ValidationError("Selected slot is no longer available.")

    _validate_booking_window(
        appointment.patient,
        new_slot.doctor,
        new_slot.start_datetime,
        new_slot.end_datetime,
        exclude_appointment_id=appointment.id,
    )

    old_slot.status = AppointmentSlot.Status.AVAILABLE
    new_slot.status = AppointmentSlot.Status.BOOKED
    old_slot.save(update_fields=["status", "updated_at"])
    new_slot.save(update_fields=["status", "updated_at"])

    old_start = appointment.scheduled_start
    old_end = appointment.scheduled_end

    appointment.slot = new_slot
    appointment.scheduled_start = new_slot.start_datetime
    appointment.scheduled_end = new_slot.end_datetime
    appointment.save(update_fields=["slot", "scheduled_start", "scheduled_end", "updated_at"])

    if appointment.status != Appointment.Status.REQUESTED:
        transition_appointment(appointment, Appointment.Status.REQUESTED, changed_by=changed_by, reason=reason)
        appointment.refresh_from_db()

    AppointmentRescheduleHistory.objects.create(
        appointment=appointment,
        old_start_datetime=old_start,
        old_end_datetime=old_end,
        new_start_datetime=new_slot.start_datetime,
        new_end_datetime=new_slot.end_datetime,
        changed_by=changed_by,
        reason=reason,
    )
    return appointment
