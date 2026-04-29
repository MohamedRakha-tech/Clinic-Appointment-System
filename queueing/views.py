from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import date

from appointments.models import Appointment
from accounts.mixins import DoctorRequiredMixin, ReceptionistRequiredMixin
from accounts.models import DoctorProfile
from .models import AppointmentCheckin
from .forms import CheckInForm

class QueueService:

    @staticmethod
    @transaction.atomic
    def check_in_patient(appointment_id: int, checked_in_by) -> AppointmentCheckin:
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)

        if appointment.status != Appointment.Status.CONFIRMED:
            raise ValidationError("Only CONFIRMED appointments can be checked in.")

        if hasattr(appointment, 'checkin'):
            raise ValidationError("Patient already checked in.")

        position = AppointmentCheckin.objects.filter(
            appointment__doctor=appointment.doctor,
            appointment__scheduled_start__date=appointment.scheduled_start.date(),
        ).count() + 1

        appointment.status = Appointment.Status.CHECKED_IN
        appointment.checked_in_by = checked_in_by
        appointment.save(update_fields=['status', 'checked_in_by', 'updated_at'])

        return AppointmentCheckin.objects.create(
            appointment=appointment,
            checked_in_at=timezone.now(),
            checked_in_by=checked_in_by,
            queue_number=position,
        )

class CheckInView(ReceptionistRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        form = CheckInForm()
        return render(request, 'queueing/checkin.html', {
            'appointment': appointment,
            'form': form
        })

    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        form = CheckInForm(request.POST)

        if form.is_valid():
            try:
                queue_entry = QueueService.check_in_patient(appointment_id, request.user)
                return redirect('queueing:reception_queue')
            except ValidationError as e:
                form.add_error(None, str(e))
                return render(request, 'queueing/checkin.html', {
                    'appointment': appointment,
                    'form': form,
                    'error': str(e)
                })

        return render(request, 'queueing/checkin.html', {
            'appointment': appointment,
            'form': form
        })


class DoctorQueueView(DoctorRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request):
        try:
            doctor_profile = request.user.doctor_profile
        except (DoctorProfile.DoesNotExist, AttributeError):
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            }, status=403)

        queue_entries = AppointmentCheckin.objects.filter(
            appointment__doctor=doctor_profile,
            appointment__scheduled_start__date=date.today(),
            appointment__status=Appointment.Status.CHECKED_IN,
        ).select_related(
            'appointment',
            'appointment__patient',
            'appointment__patient__user'
        ).order_by('checked_in_at')

        return render(request, 'queueing/doctor_queue.html', {
            'queue_entries': queue_entries,
            'doctor': doctor_profile,
        })


class ReceptionQueueMonitorView(ReceptionistRequiredMixin, View):

    login_url = '/accounts/login/'

    def get(self, request):
        pending_checkins = Appointment.objects.filter(
            status=Appointment.Status.CONFIRMED,
            scheduled_start__date=date.today(),
        ).select_related(
            'patient',
            'patient__user',
            'doctor',
            'doctor__user'
        ).order_by('scheduled_start')

        queue_entries = AppointmentCheckin.objects.filter(
            appointment__scheduled_start__date=date.today(),
            appointment__status=Appointment.Status.CHECKED_IN,
        ).select_related(
            'appointment',
            'appointment__doctor',
            'appointment__doctor__user',
            'appointment__patient',
            'appointment__patient__user'
        ).order_by('appointment__doctor', 'checked_in_at')

        doctors_queue = {}
        for entry in queue_entries:
            doctor_id = entry.appointment.doctor.id
            if doctor_id not in doctors_queue:
                doctors_queue[doctor_id] = {
                    'doctor': entry.appointment.doctor,
                    'queue': []
                }
            doctors_queue[doctor_id]['queue'].append(entry)

        return render(request, 'queueing/reception_queue_monitor.html', {
            'doctors_queue': doctors_queue,
            'pending_checkins': pending_checkins,
        })
