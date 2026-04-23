from django.db import models

from appointments.models import Appointment
from accounts.models import DoctorProfile


# ─────────────────────────────────────────────
# SELECTORS (Read-Only Queries)
# ─────────────────────────────────────────────

def has_consultation_record(appointment_id: int) -> bool:
    """
    Check if consultation record exists for an appointment.
    Used by appointments service to guard COMPLETED transition.
    """
    return ConsultationRecord.objects.filter(
        appointment_id=appointment_id
    ).exists()


def get_doctor_consultations(doctor_id: int, limit: int = None):
    """Get consultation records for a doctor."""
    queryset = (
        ConsultationRecord.objects
        .filter(doctor_id=doctor_id)
        .select_related(
            'appointment',
            'appointment__patient',
            'appointment__patient__user'
        )
        .order_by('-created_at')
    )
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


# ─────────────────────────────────────────────
# MEDICAL RECORDS
# ─────────────────────────────────────────────

class ConsultationRecord(models.Model):
    appointment          = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="consultation_record")
    doctor               = models.ForeignKey(DoctorProfile, on_delete=models.RESTRICT, related_name="consultation_records")
    diagnosis            = models.TextField()
    notes                = models.TextField()
    requested_tests      = models.TextField(blank=True, null=True)  # free-text; use RequestedTest for normalized entries
    summary_for_patient  = models.TextField()
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "consultation_records"

    def __str__(self):
        return f"Consultation for Appointment {self.appointment_id}"


class PrescriptionItem(models.Model):
    consultation_record = models.ForeignKey(ConsultationRecord, on_delete=models.CASCADE, related_name="prescription_items")
    drug_name           = models.CharField(max_length=255)
    dose                = models.CharField(max_length=120)
    duration            = models.CharField(max_length=120)
    instructions        = models.CharField(max_length=255, blank=True, null=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prescription_items"
        indexes  = [
            models.Index(fields=["consultation_record"], name="idx_prescription_consultation"),
        ]

    def __str__(self):
        return f"{self.drug_name} ({self.dose}) for Record {self.consultation_record_id}"


class RequestedTest(models.Model):
    consultation_record = models.ForeignKey(ConsultationRecord, on_delete=models.CASCADE, related_name="requested_tests_normalized")
    test_name           = models.CharField(max_length=255)
    notes               = models.CharField(max_length=255, blank=True, null=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "requested_tests"
        indexes  = [
            models.Index(fields=["consultation_record"], name="idx_req_tests_consult"),
        ]

    def __str__(self):
        return f"{self.test_name} for Record {self.consultation_record_id}"
