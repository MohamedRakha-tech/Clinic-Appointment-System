from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.core.exceptions import ValidationError
from datetime import date, datetime, time
from django.utils import timezone

from appointments.models import Appointment
from accounts.mixins import ClinicStaffRequiredMixin, DoctorRequiredMixin, ReceptionistRequiredMixin
from accounts.models import DoctorProfile
from .models import AppointmentCheckin
from .forms import CheckInForm
from .services import QueueService

class CheckInView(ClinicStaffRequiredMixin, View):

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

        today = timezone.localdate()
        start_of_day = timezone.make_aware(datetime.combine(today, time.min))
        end_of_day = timezone.make_aware(datetime.combine(today, time.max))

        queue_entries = AppointmentCheckin.objects.filter(
            appointment__doctor=doctor_profile,
            appointment__scheduled_start__gte=start_of_day,
            appointment__scheduled_start__lte=end_of_day,
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
        today = timezone.localdate()
        selected_date = today
        raw_date = request.GET.get("date")
        if raw_date:
            try:
                selected_date = date.fromisoformat(raw_date)
            except ValueError:
                selected_date = today

        read_only = selected_date != today

        start_of_day = timezone.make_aware(datetime.combine(selected_date, time.min))
        end_of_day = timezone.make_aware(datetime.combine(selected_date, time.max))

        pending_checkins = Appointment.objects.filter(
            status=Appointment.Status.CONFIRMED,
            scheduled_start__gte=start_of_day,
            scheduled_start__lte=end_of_day,
        ).select_related(
            'patient',
            'patient__user',
            'doctor',
            'doctor__user'
        ).order_by('scheduled_start')

        queue_entries = AppointmentCheckin.objects.filter(
            appointment__scheduled_start__gte=start_of_day,
            appointment__scheduled_start__lte=end_of_day,
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
            'selected_date': selected_date,
            'read_only': read_only,
        })
