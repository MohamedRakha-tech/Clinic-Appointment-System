from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import date

from appointments.models import Appointment
from accounts.models import DoctorProfile
from .models import ConsultationRecord, PrescriptionItem, RequestedTest
from .forms import ConsultationRecordForm, PrescriptionItemForm, RequestedTestForm


# ─────────────────────────────────────────────
# SERVICES (Business Logic)
# ─────────────────────────────────────────────

class EMRService:
    """Service for EMR and consultation operations."""

    @staticmethod
    @transaction.atomic
    def create_consultation_record(appointment_id: int, doctor: DoctorProfile, data: dict) -> ConsultationRecord:
        """
        Create a new consultation record.
        Doctor must own the appointment and appointment must be CHECKED_IN.
        """
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)

        # Validate doctor ownership
        if appointment.doctor != doctor:
            raise ValidationError("You can only create records for your own appointments.")

        # Validate appointment status
        if appointment.status != Appointment.Status.CHECKED_IN:
            raise ValidationError("Patient must be checked in (CHECKED_IN status).")

        # Prevent duplicate consultation
        if hasattr(appointment, 'consultation_record'):
            raise ValidationError("Consultation record already exists for this appointment.")

        # Create consultation record
        consultation = ConsultationRecord.objects.create(
            appointment=appointment,
            doctor=doctor,
            diagnosis=data.get('diagnosis', ''),
            notes=data.get('notes', ''),
            summary_for_patient=data.get('summary_for_patient', ''),
        )

        return consultation

    @staticmethod
    @transaction.atomic
    def update_consultation_record(consultation_id: int, doctor: DoctorProfile, data: dict) -> ConsultationRecord:
        """Update an existing consultation record (doctor only)."""
        consultation = ConsultationRecord.objects.select_for_update().get(id=consultation_id)

        # Validate doctor ownership
        if consultation.doctor != doctor:
            raise ValidationError("You can only edit your own consultation records.")

        # Update fields
        consultation.diagnosis = data.get('diagnosis', consultation.diagnosis)
        consultation.notes = data.get('notes', consultation.notes)
        consultation.summary_for_patient = data.get('summary_for_patient', consultation.summary_for_patient)
        consultation.save()

        return consultation

    @staticmethod
    def get_doctor_consultations(doctor: DoctorProfile, limit: int = None):
        """Get all consultation records for a doctor."""
        queryset = ConsultationRecord.objects.filter(
            doctor=doctor
        ).select_related(
            'appointment',
            'appointment__patient',
            'appointment__patient__user'
        ).order_by('-created_at')

        if limit:
            queryset = queryset[:limit]

        return list(queryset)


# ─────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────

class ConsultationListView(View):
    """Doctor views list of their consultations."""

    def get(self, request):
        try:
            doctor_profile = request.user.doctor_profile
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            })

        consultations = EMRService.get_doctor_consultations(doctor_profile)

        return render(request, 'emr/consultations_list.html', {
            'consultations': consultations,
            'doctor': doctor_profile,
        })


class ConsultationDetailView(View):
    """View consultation record details with prescriptions and tests."""

    def get(self, request, pk):
        consultation = get_object_or_404(
            ConsultationRecord.objects.select_related(
                'doctor',
                'appointment',
                'appointment__patient',
                'appointment__patient__user'
            ).prefetch_related(
                'prescription_items',
                'requested_tests_normalized'
            ),
            pk=pk
        )

        # Only doctor who created it can view (or admin)
        if consultation.doctor.user != request.user and not request.user.is_staff:
            return render(request, 'error.html', {
                'error': 'Permission denied'
            }, status=403)

        return render(request, 'emr/consultation_detail.html', {
            'consultation': consultation,
            'prescriptions': consultation.prescription_items.all(),
            'tests': consultation.requested_tests_normalized.all(),
        })


class ConsultationCreateView(View):
    """Doctor creates a consultation record for a checked-in appointment."""

    def get(self, request, appointment_id):
        appointment = get_object_or_404(
            Appointment.objects.select_related('patient', 'patient__user', 'doctor'),
            pk=appointment_id
        )

        # Validate appointment belongs to requesting doctor
        try:
            doctor_profile = request.user.doctor_profile
            if appointment.doctor != doctor_profile:
                return render(request, 'error.html', {
                    'error': 'Permission denied'
                }, status=403)
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        form = ConsultationRecordForm()
        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'appointment': appointment,
            'action': 'Create',
        })

    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)

        try:
            doctor_profile = request.user.doctor_profile
            if appointment.doctor != doctor_profile:
                return render(request, 'error.html', {
                    'error': 'Permission denied'
                }, status=403)
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        form = ConsultationRecordForm(request.POST)

        if form.is_valid():
            try:
                consultation = EMRService.create_consultation_record(
                    appointment_id,
                    doctor_profile,
                    form.cleaned_data
                )
                return redirect('emr:detail', pk=consultation.id)
            except ValidationError as e:
                form.add_error(None, str(e))
                return render(request, 'emr/consultation_form.html', {
                    'form': form,
                    'appointment': appointment,
                    'action': 'Create',
                    'error': str(e),
                })

        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'appointment': appointment,
            'action': 'Create',
        })


class ConsultationUpdateView(View):
    """Doctor updates consultation record."""

    def get(self, request, pk):
        consultation = get_object_or_404(
            ConsultationRecord.objects.select_related('appointment', 'appointment__patient'),
            pk=pk
        )

        try:
            doctor_profile = request.user.doctor_profile
            if consultation.doctor != doctor_profile:
                return render(request, 'error.html', {
                    'error': 'Permission denied'
                }, status=403)
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        form = ConsultationRecordForm(instance=consultation)
        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'consultation': consultation,
            'action': 'Edit',
        })

    def post(self, request, pk):
        consultation = get_object_or_404(ConsultationRecord, pk=pk)

        try:
            doctor_profile = request.user.doctor_profile
            if consultation.doctor != doctor_profile:
                return render(request, 'error.html', {
                    'error': 'Permission denied'
                }, status=403)
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        form = ConsultationRecordForm(request.POST, instance=consultation)

        if form.is_valid():
            try:
                consultation = EMRService.update_consultation_record(
                    pk,
                    doctor_profile,
                    form.cleaned_data
                )
                return redirect('emr:detail', pk=consultation.id)
            except ValidationError as e:
                form.add_error(None, str(e))
                return render(request, 'emr/consultation_form.html', {
                    'form': form,
                    'consultation': consultation,
                    'action': 'Edit',
                    'error': str(e),
                })

        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'consultation': consultation,
            'action': 'Edit',
        })


class ConsultationDeleteView(View):
    """Doctor deletes a consultation record."""

    def get(self, request, pk):
        consultation = get_object_or_404(ConsultationRecord, pk=pk)

        try:
            doctor_profile = request.user.doctor_profile
            if consultation.doctor != doctor_profile:
                return render(request, 'error.html', {
                    'error': 'Permission denied'
                }, status=403)
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        return render(request, 'emr/consultation_delete.html', {
            'consultation': consultation,
        })

    def post(self, request, pk):
        consultation = get_object_or_404(ConsultationRecord, pk=pk)

        try:
            doctor_profile = request.user.doctor_profile
            if consultation.doctor != doctor_profile:
                return render(request, 'error.html', {
                    'error': 'Permission denied'
                }, status=403)
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        consultation.delete()
        return redirect('emr:list')
