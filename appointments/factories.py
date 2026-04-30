import factory
from factory.django import DjangoModelFactory
from uuid import uuid4

from accounts.factories import DoctorProfileFactory, PatientProfileFactory
from .models import Appointment
from scheduling.factories import AppointmentSlotFactory


class AppointmentFactory(DjangoModelFactory):
    class Meta:
        model = Appointment

    appointment_code = factory.LazyFunction(lambda: f"APT-{uuid4().hex[:12].upper()}")
    patient = factory.SubFactory(PatientProfileFactory)
    doctor = factory.SubFactory(DoctorProfileFactory)
    slot = factory.LazyAttribute(lambda obj: AppointmentSlotFactory(doctor=obj.doctor))
    scheduled_start = factory.LazyAttribute(lambda obj: obj.slot.start_datetime)
    scheduled_end = factory.LazyAttribute(lambda obj: obj.slot.end_datetime)
    status = Appointment.Status.REQUESTED
    booking_source = Appointment.BookingSource.PATIENT
    confirmed_by = None
    checked_in_by = None
    cancelled_by = None
    cancellation_reason = None
    notes_for_staff = None

    @factory.post_generation
    def mark_slot_booked(obj, create, extracted, **kwargs):
        if not create or not obj.slot_id:
            return

        if obj.status != Appointment.Status.CANCELLED and obj.slot.status != "BOOKED":
            obj.slot.status = "BOOKED"
            obj.slot.save(update_fields=["status", "updated_at"])
