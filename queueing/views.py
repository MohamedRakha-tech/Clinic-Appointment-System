from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import date

from appointments.models import Appointment
from accounts.models import DoctorProfile
from .models import AppointmentCheckin
from .forms import CheckInForm


# ─────────────────────────────────────────────
# SERVICES (Business Logic)
# ─────────────────────────────────────────────

class QueueService:
    """Service for queue management operations."""

    @staticmethod
    @transaction.atomic
    def check_in_patient(appointment_id: int, checked_in_by) -> AppointmentCheckin:
        """
        Check in a confirmed appointment.
        Assigns queue position and transitions appointment status.
        """
        appointment = Appointment.objects.select_for_update().get(id=appointment_id)

        if appointment.status != Appointment.Status.CONFIRMED:
            raise ValidationError("Only CONFIRMED appointments can be checked in.")

        if hasattr(appointment, 'checkin'):
            raise ValidationError("Patient already checked in.")

        # Calculate queue position: count checked-ins for this doctor today
        position = AppointmentCheckin.objects.filter(
            appointment__doctor=appointment.doctor,
            appointment__scheduled_start__date=appointment.scheduled_start.date(),
        ).count() + 1

        # Transition appointment to CHECKED_IN
        appointment.status = Appointment.Status.CHECKED_IN
        appointment.checked_in_by = checked_in_by
        appointment.save(update_fields=['status', 'checked_in_by', 'updated_at'])

        # Create queue entry
        return AppointmentCheckin.objects.create(
            appointment=appointment,
            checked_in_at=timezone.now(),
            checked_in_by=checked_in_by,
            queue_number=position,
        )


# ─────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────

class CheckInView(View):
    """Receptionist checks in a patient."""

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
                return redirect('queueing:doctor_queue')
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


class DoctorQueueView(View):
    """Doctor views their queue for the current day."""

    def get(self, request):
        try:
            doctor_profile = request.user.doctor_profile
        except DoctorProfile.DoesNotExist:
            return render(request, 'error.html', {
                'error': 'User does not have doctor profile'
            })

        # Get all checked-in appointments for today, ordered by check-in time
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


class ReceptionQueueMonitorView(View):
    """Receptionist monitors queues for all doctors."""

    def get(self, request):
        # Get all checked-in appointments for today, grouped by doctor
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

        # Group by doctor
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
        })
