from itertools import count

from django.utils import timezone

from accounts.factories import DoctorProfileFactory, PatientProfileFactory, UserFactory
from appointments.models import Appointment
from scheduling.factories import AppointmentSlotFactory


_appointment_seq = count(1)


def AppointmentFactory(**kwargs):
    patient = kwargs.pop("patient", None) or PatientProfileFactory()
    doctor = kwargs.pop("doctor", None) or DoctorProfileFactory()
    slot = kwargs.pop("slot", None) or AppointmentSlotFactory(doctor=doctor)
    appointment_code = kwargs.pop("appointment_code", f"APT-{next(_appointment_seq):08d}")
    kwargs.setdefault("status", Appointment.Status.REQUESTED)
    kwargs.setdefault("booking_source", Appointment.BookingSource.PATIENT)
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
