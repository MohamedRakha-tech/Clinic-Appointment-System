from random import choice

from accounts.factories import DoctorProfileFactory
from appointments.factories import AppointmentFactory
from emr.models import ConsultationRecord, PrescriptionItem, RequestedTest


def ConsultationRecordFactory(**kwargs):
    appointment = kwargs.pop("appointment", None) or AppointmentFactory(status="COMPLETED")
    doctor = kwargs.pop("doctor", None) or appointment.doctor or DoctorProfileFactory()
    kwargs.setdefault(
        "diagnosis",
        choice(
            [
                "Acute viral upper respiratory infection",
                "Seasonal allergic rhinitis",
                "Gastritis",
                "Musculoskeletal pain",
            ]
        ),
    )
    kwargs.setdefault(
        "notes",
        choice(
            [
                "Patient reports fever and cough.",
                "Mild headache and fatigue noted.",
                "Symptoms improving with rest.",
                "Follow-up consultation completed.",
            ]
        ),
    )
    kwargs.setdefault("requested_tests", choice(["CBC", "FBS", "Lipid profile", "No additional tests"]))
    kwargs.setdefault(
        "summary_for_patient",
        choice(
            [
                "Rest, hydration, and follow-up if symptoms worsen.",
                "Continue prescribed medication and return for review.",
                "Monitor symptoms and report any deterioration.",
                "Patient advised on self-care and red-flag symptoms.",
            ]
        ),
    )
    appointment.status = "COMPLETED"
    appointment.save(update_fields=["status", "updated_at"])
    return ConsultationRecord.objects.create(
        appointment=appointment,
        doctor=doctor,
        **kwargs,
    )


def PrescriptionItemFactory(**kwargs):
    consultation_record = kwargs.pop("consultation_record", None) or ConsultationRecordFactory()
    kwargs.setdefault("drug_name", choice(["Amoxicillin", "Paracetamol", "Ibuprofen", "Cetirizine", "Omeprazole"]))
    kwargs.setdefault("dose", choice(["250mg", "500mg", "10mg", "20mg"]))
    kwargs.setdefault("duration", choice(["3 days", "5 days", "7 days", "14 days"]))
    kwargs.setdefault("frequency", choice(["OD", "BD", "TDS", "SOS"]))
    kwargs.setdefault("instructions", choice(["Take after meals.", "Take with plenty of water.", "Avoid driving if drowsy.", None]))
    return PrescriptionItem.objects.create(consultation_record=consultation_record, **kwargs)


def RequestedTestFactory(**kwargs):
    consultation_record = kwargs.pop("consultation_record", None) or ConsultationRecordFactory()
    kwargs.setdefault("test_name", choice(["CBC", "FBS", "Lipid Profile", "HbA1c", "Urine Analysis"]))
    kwargs.setdefault("urgency", choice(["routine", "urgent", "stat"]))
    kwargs.setdefault("notes", choice(["Fasting required.", "Report to lab before noon.", None, "Clinical correlation advised."]))
    return RequestedTest.objects.create(consultation_record=consultation_record, **kwargs)
