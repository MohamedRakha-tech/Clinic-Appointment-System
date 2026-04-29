from django.utils import timezone

from accounts.factories import DoctorProfileFactory
from appointments.factories import AppointmentFactory
from emr.models import ConsultationRecord, PrescriptionItem, RequestedTest


def ConsultationRecordFactory(**kwargs):
    appointment = kwargs.pop("appointment", None) or AppointmentFactory(status="CHECKED_IN")
    doctor = kwargs.pop("doctor", None) or appointment.doctor or DoctorProfileFactory()
    kwargs.setdefault("diagnosis", "Acute viral upper respiratory infection")
    kwargs.setdefault("notes", "Patient reports fever and cough.")
    kwargs.setdefault("requested_tests", "CBC")
    kwargs.setdefault("summary_for_patient", "Rest, hydration, and follow-up if symptoms worsen.")
    appointment.status = "CHECKED_IN"
    appointment.save(update_fields=["status", "updated_at"])
    return ConsultationRecord.objects.create(
        appointment=appointment,
        doctor=doctor,
        **kwargs,
    )


def PrescriptionItemFactory(**kwargs):
    consultation_record = kwargs.pop("consultation_record", None) or ConsultationRecordFactory()
    kwargs.setdefault("drug_name", "Amoxicillin")
    kwargs.setdefault("dose", "500mg")
    kwargs.setdefault("duration", "7 days")
    return PrescriptionItem.objects.create(consultation_record=consultation_record, **kwargs)


def RequestedTestFactory(**kwargs):
    consultation_record = kwargs.pop("consultation_record", None) or ConsultationRecordFactory()
    kwargs.setdefault("test_name", "CBC")
    return RequestedTest.objects.create(consultation_record=consultation_record, **kwargs)
