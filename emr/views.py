from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.core.exceptions import ValidationError

from appointments.models import Appointment
from accounts.models import DoctorProfile
from .models import ConsultationRecord, PrescriptionItem, RequestedTest
from .forms import ConsultationRecordForm, PrescriptionItemForm, RequestedTestForm

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

class ConsultationListView(LoginRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        doctor_profile = _get_doctor_profile(request)
        if not doctor_profile:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            })

        consultations = EMRService.get_doctor_consultations(doctor_profile)

        return render(request, 'emr/consultations_list.html', {
            'consultations': consultations,
            'doctor': doctor_profile,
        })


class PatientConsultationListView(LoginRequiredMixin, View):

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

        patient_profile = _get_patient_profile(request)
        can_manage = consultation.doctor.user == request.user or request.user.is_staff
        can_view = can_manage or (patient_profile and consultation.appointment.patient_id == patient_profile.id)

        if not can_view:
            return render(request, 'error.html', {
                'error': 'Permission denied'
            }, status=403)

        return render(request, 'emr/consultation_detail.html', {
            'consultation': consultation,
            'prescriptions': consultation.prescription_items.all(),
            'tests': consultation.requested_tests_normalized.all(),
            'can_manage': can_manage,
            'is_patient_view': bool(patient_profile and consultation.appointment.patient_id == patient_profile.id),
        })


class ConsultationCreateView(LoginRequiredMixin, View):

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
        return render(request, 'emr/consultation_form.html', {
            'form': form,
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


class ConsultationUpdateView(LoginRequiredMixin, View):

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
        return render(request, 'emr/consultation_form.html', {
            'form': form,
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
                    'appointment': consultation.appointment,
                    'action': 'Edit',
                    'error': str(e),
                })

        return render(request, 'emr/consultation_form.html', {
            'form': form,
            'consultation': consultation,
            'appointment': consultation.appointment,
            'action': 'Edit',
        })


class ConsultationDeleteView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'

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
