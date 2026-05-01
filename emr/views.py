from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.core.exceptions import ValidationError

from appointments.models import Appointment
from appointments.services import transition_appointment
from accounts.mixins import DoctorRequiredMixin, PatientRequiredMixin, ReceptionistRequiredMixin
from accounts.models import DoctorProfile
from accounts.utils import get_user_role
from .models import ConsultationRecord, PrescriptionItem, RequestedTest
from .forms import ConsultationRecordForm, PrescriptionItemForm, RequestedTestForm, PrescriptionItemFormSet, RequestedTestFormSet

class EMRService:

    @staticmethod
    @transaction.atomic
    def create_consultation_record(appointment_id: int, doctor: DoctorProfile, data: dict) -> ConsultationRecord:
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)

        if appointment.doctor != doctor:
            raise ValidationError("You can only create records for your own appointments.")

        if appointment.status != Appointment.Status.CHECKED_IN:
            raise ValidationError("Patient must be checked in (CHECKED_IN status).")

        if hasattr(appointment, 'consultation_record'):
            raise ValidationError("Consultation record already exists for this appointment.")

        consultation = ConsultationRecord.objects.create(
            appointment=appointment,
            doctor=doctor,
            diagnosis=data.get('diagnosis', ''),
            notes=data.get('notes', ''),
            requested_tests=data.get('requested_tests', ''),
            summary_for_patient=data.get('summary_for_patient', ''),
        )

        transition_appointment(
            appointment,
            Appointment.Status.COMPLETED,
            changed_by=doctor.user,
            reason="Consultation completed",
        )

        return consultation

    @staticmethod
    @transaction.atomic
    def update_consultation_record(consultation_id: int, doctor: DoctorProfile, data: dict) -> ConsultationRecord:
        consultation = ConsultationRecord.objects.select_for_update().get(id=consultation_id)

        if consultation.doctor != doctor:
            raise ValidationError("You can only edit your own consultation records.")

        consultation.diagnosis = data.get('diagnosis', consultation.diagnosis)
        consultation.notes = data.get('notes', consultation.notes)
        consultation.requested_tests = data.get('requested_tests', consultation.requested_tests)
        consultation.summary_for_patient = data.get('summary_for_patient', consultation.summary_for_patient)
        consultation.save()

        return consultation

    @staticmethod
    def get_doctor_consultations(doctor: DoctorProfile, limit: int = None):
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


def _get_doctor_profile(request):
    try:
        return request.user.doctor_profile
    except (DoctorProfile.DoesNotExist, AttributeError):
        return None


def _get_patient_profile(request):
    try:
        return request.user.patient_profile
    except AttributeError:
        return None

class ConsultationListView(DoctorRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request):
        doctor_profile = _get_doctor_profile(request)
        if not doctor_profile:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            })

        consultations = EMRService.get_doctor_consultations(doctor_profile)

        return render(request, 'emr/consultations_list.html', {
            'consultations': consultations,
            'doctor': doctor_profile,
            'header_title': 'Consultation Timeline',
            'header_subtitle': 'Review, continue, and manage your clinical notes quickly.',
            'records_title': 'My Consultation Records',
            'viewer_label': f"Dr. {doctor_profile.user.first_name or doctor_profile.user.username}",
            'show_edit_actions': True,
        })


class ReceptionConsultationListView(ReceptionistRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request):
        consultations = ConsultationRecord.objects.select_related(
            'doctor',
            'doctor__user',
            'appointment',
            'appointment__patient',
            'appointment__patient__user'
        ).order_by('-created_at')

        return render(request, 'emr/consultations_list.html', {
            'consultations': consultations,
            'header_title': 'EMR Records',
            'header_subtitle': 'Access completed consultation summaries and orders.',
            'records_title': 'Consultation Records',
            'viewer_label': 'Reception',
            'show_edit_actions': False,
        })


class PatientConsultationListView(PatientRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request):
        patient_profile = _get_patient_profile(request)
        if not patient_profile:
            return render(request, 'error.html', {
                'error': 'User does not have patient profile'
            }, status=403)

        consultations = ConsultationRecord.objects.filter(
            appointment__patient=patient_profile
        ).select_related(
            'doctor',
            'doctor__user',
            'appointment',
            'appointment__patient',
            'appointment__patient__user'
        ).order_by('-created_at')

        return render(request, 'emr/patient_consultations_list.html', {
            'consultations': consultations,
            'patient': patient_profile,
        })


class ConsultationDetailView(LoginRequiredMixin, View):

    login_url = '/accounts/login/'

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

        role = get_user_role(request.user)
        patient_profile = _get_patient_profile(request)
        is_receptionist = role == "receptionist"
        can_manage = consultation.doctor.user == request.user or request.user.is_superuser or hasattr(request.user, "admin_profile")
        can_view = can_manage or is_receptionist or (patient_profile and consultation.appointment.patient_id == patient_profile.id)

        if not can_view:
            return render(request, 'error.html', {
                'error': 'Permission denied'
            }, status=403)

        if is_receptionist:
            back_url = reverse('emr:reception_list')
            back_label = 'Back to EMR Records'
        elif patient_profile and consultation.appointment.patient_id == patient_profile.id:
            back_url = reverse('emr:patient_list')
            back_label = 'Back to My Consultations'
        else:
            back_url = reverse('emr:list')
            back_label = 'Back'

        return render(request, 'emr/consultation_detail.html', {
            'consultation': consultation,
            'prescriptions': consultation.prescription_items.all(),
            'tests': consultation.requested_tests_normalized.all(),
            'can_manage': can_manage,
            'is_patient_view': bool(patient_profile and consultation.appointment.patient_id == patient_profile.id),
            'show_clinical_notes': role == "doctor",
            'show_diagnosis': role != "patient",
            'back_url': back_url,
            'back_label': back_label,
        })


class ConsultationCreateView(DoctorRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request, appointment_id):
        appointment = get_object_or_404(
            Appointment.objects.select_related('patient', 'patient__user', 'doctor'),
            pk=appointment_id
        )

        doctor_profile = _get_doctor_profile(request)
        if not doctor_profile:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        if appointment.doctor != doctor_profile:
            return render(request, 'error.html', {
                'error': 'Permission denied'
            }, status=403)

        if appointment.status != Appointment.Status.CHECKED_IN:
            return render(request, 'error.html', {
                'error': 'Only checked-in appointments can start a consultation'
            }, status=403)

        if hasattr(appointment, 'consultation_record'):
            return render(request, 'error.html', {
                'error': 'Consultation record already exists for this appointment'
            }, status=403)

        form = ConsultationRecordForm()
        prescription_formset = PrescriptionItemFormSet(prefix='prescriptions')
        test_formset = RequestedTestFormSet(prefix='tests')
        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'prescription_formset': prescription_formset,
            'test_formset': test_formset,
            'appointment': appointment,
            'action': 'Create',
        })

    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)

        doctor_profile = _get_doctor_profile(request)
        if not doctor_profile:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        if appointment.doctor != doctor_profile:
            return render(request, 'error.html', {
                'error': 'Permission denied'
            }, status=403)

        if appointment.status != Appointment.Status.CHECKED_IN:
            return render(request, 'error.html', {
                'error': 'Only checked-in appointments can start a consultation'
            }, status=403)

        if hasattr(appointment, 'consultation_record'):
            return render(request, 'error.html', {
                'error': 'Consultation record already exists for this appointment'
            }, status=403)

        form = ConsultationRecordForm(request.POST)
        prescription_formset = PrescriptionItemFormSet(request.POST, prefix='prescriptions')
        test_formset = RequestedTestFormSet(request.POST, prefix='tests')

        if form.is_valid() and prescription_formset.is_valid() and test_formset.is_valid():
            try:
                with transaction.atomic():
                    consultation = EMRService.create_consultation_record(
                        appointment_id,
                        doctor_profile,
                        form.cleaned_data
                    )
                    prescription_formset.instance = consultation
                    prescription_formset.save()
                    test_formset.instance = consultation
                    test_formset.save()
                return redirect('emr:detail', pk=consultation.id)
            except ValidationError as e:
                form.add_error(None, str(e))
                return render(request, 'emr/consultation_form.html', {
                    'form': form,
                    'prescription_formset': prescription_formset,
                    'test_formset': test_formset,
                    'appointment': appointment,
                    'action': 'Create',
                    'error': str(e),
                })

        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'prescription_formset': prescription_formset,
            'test_formset': test_formset,
            'appointment': appointment,
            'action': 'Create',
        })


class ConsultationUpdateView(DoctorRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request, pk):
        consultation = get_object_or_404(
            ConsultationRecord.objects.select_related('appointment', 'appointment__patient'),
            pk=pk
        )

        doctor_profile = _get_doctor_profile(request)
        if not doctor_profile:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        if consultation.doctor != doctor_profile:
            return render(request, 'error.html', {
                'error': 'Permission denied'
            }, status=403)

        form = ConsultationRecordForm(instance=consultation)
        prescription_formset = PrescriptionItemFormSet(instance=consultation, prefix='prescriptions')
        test_formset = RequestedTestFormSet(instance=consultation, prefix='tests')
        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'prescription_formset': prescription_formset,
            'test_formset': test_formset,
            'consultation': consultation,
            'appointment': consultation.appointment,
            'action': 'Edit',
        })

    def post(self, request, pk):
        consultation = get_object_or_404(ConsultationRecord, pk=pk)

        doctor_profile = _get_doctor_profile(request)
        if not doctor_profile:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        if consultation.doctor != doctor_profile:
            return render(request, 'error.html', {
                'error': 'Permission denied'
            }, status=403)

        form = ConsultationRecordForm(request.POST, instance=consultation)
        prescription_formset = PrescriptionItemFormSet(request.POST, instance=consultation, prefix='prescriptions')
        test_formset = RequestedTestFormSet(request.POST, instance=consultation, prefix='tests')

        if form.is_valid() and prescription_formset.is_valid() and test_formset.is_valid():
            try:
                with transaction.atomic():
                    consultation = EMRService.update_consultation_record(
                        pk,
                        doctor_profile,
                        form.cleaned_data
                    )
                    prescription_formset.save()
                    test_formset.save()
                return redirect('emr:detail', pk=consultation.id)
            except ValidationError as e:
                form.add_error(None, str(e))
                return render(request, 'emr/consultation_form.html', {
                    'form': form,
                    'prescription_formset': prescription_formset,
                    'test_formset': test_formset,
                    'consultation': consultation,
                    'appointment': consultation.appointment,
                    'action': 'Edit',
                    'error': str(e),
                })

        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'prescription_formset': prescription_formset,
            'test_formset': test_formset,
            'consultation': consultation,
            'appointment': consultation.appointment,
            'action': 'Edit',
        })


class ConsultationDeleteView(DoctorRequiredMixin, View):

    def get(self, request, pk):
        consultation = get_object_or_404(ConsultationRecord, pk=pk)

        doctor_profile = _get_doctor_profile(request)
        if not doctor_profile:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        if consultation.doctor != doctor_profile:
            return render(request, 'error.html', {
                'error': 'Permission denied'
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
