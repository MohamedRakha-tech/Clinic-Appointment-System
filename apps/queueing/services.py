from datetime import datetime, timedelta
from typing import List, Optional
from django.utils import timezone
from django.db import transaction
from apps.accounts.models import DoctorProfile, User
from apps.appointments.models import Appointment
from apps.appointments.services import AppointmentStatusService


class QueueManagementService:
    """Service for managing patient queues and check-in functionality"""
    
    @staticmethod
    def get_doctor_queue(doctor: DoctorProfile, target_date: Optional[datetime] = None) -> List[Appointment]:
        """
        Get the current queue for a doctor
        
        Args:
            doctor: Doctor profile to get queue for
            target_date: Optional date to get queue for (defaults to today)
            
        Returns:
            List of appointments in queue order
        """
        if target_date is None:
            target_date = timezone.now().date()
        else:
            target_date = target_date.date()
        
        # Get confirmed and checked-in appointments for the day
        queue = Appointment.objects.filter(
            doctor=doctor,
            scheduled_start__date=target_date,
            status__in=[Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN]
        ).order_by('scheduled_start')
        
        return list(queue)
    
    @staticmethod
    def get_waiting_room_queue(doctor: DoctorProfile) -> List[dict]:
        """
        Get the current waiting room queue with waiting times
        
        Args:
            doctor: Doctor profile to get waiting room for
            
        Returns:
            List of dictionaries with appointment info and waiting time
        """
        target_date = timezone.now().date()
        
        # Get checked-in patients who haven't been seen yet
        waiting_appointments = Appointment.objects.filter(
            doctor=doctor,
            scheduled_start__date=target_date,
            status=Appointment.Status.CHECKED_IN
        ).order_by('checked_in_by')  # Order by check-in time
        
        waiting_queue = []
        current_time = timezone.now()
        
        for appointment in waiting_appointments:
            # Calculate waiting time
            # Find the check-in time from status history
            check_in_time = QueueManagementService._get_check_in_time(appointment)
            waiting_time = current_time - check_in_time if check_in_time else timedelta(0)
            
            waiting_queue.append({
                'appointment': appointment,
                'patient_name': f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}",
                'check_in_time': check_in_time,
                'waiting_time_minutes': int(waiting_time.total_seconds() / 60),
                'scheduled_time': appointment.scheduled_start,
                'appointment_code': appointment.appointment_code
            })
        
        return waiting_queue
    
    @staticmethod
    def _get_check_in_time(appointment: Appointment) -> Optional[datetime]:
        """Get the check-in time from status history"""
        from apps.appointments.models import AppointmentStatusHistory
        
        try:
            status_change = AppointmentStatusHistory.objects.filter(
                appointment=appointment,
                new_status=Appointment.Status.CHECKED_IN
            ).order_by('created_at').first()
            
            return status_change.created_at if status_change else None
        except:
            return None
    
    @staticmethod
    @transaction.atomic
    def check_in_patient(
        appointment: Appointment,
        checked_in_by: User,
        notes: Optional[str] = None
    ) -> tuple[Appointment, bool]:
        """
        Check in a patient for their appointment
        
        Args:
            appointment: Appointment to check in
            checked_in_by: User performing the check-in
            notes: Optional notes for the check-in
            
        Returns:
            Tuple of (updated Appointment, success boolean)
            
        Raises:
            ValidationError: If check-in rules are violated
        """
        # Validate appointment can be checked in
        if appointment.status != Appointment.Status.CONFIRMED:
            raise ValidationError("Only confirmed appointments can be checked in")
        
        # Check if it's reasonable time to check in (not too early)
        current_time = timezone.now()
        scheduled_time = appointment.scheduled_start
        
        # Allow check-in up to 30 minutes before scheduled time
        if current_time < scheduled_time - timedelta(minutes=30):
            raise ValidationError("Cannot check in more than 30 minutes before scheduled time")
        
        # Perform check-in using status service
        try:
            updated_appointment, success = AppointmentStatusService.update_appointment_status(
                appointment=appointment,
                new_status=Appointment.Status.CHECKED_IN,
                changed_by=checked_in_by,
                reason=notes or "Patient checked in"
            )
            
            return updated_appointment, success
        except Exception as e:
            raise ValidationError(f"Failed to check in patient: {str(e)}")
    
    @staticmethod
    def get_today_schedule(doctor: DoctorProfile) -> dict:
        """
        Get today's schedule summary for a doctor
        
        Args:
            doctor: Doctor profile to get schedule for
            
        Returns:
            Dictionary with schedule summary
        """
        target_date = timezone.now().date()
        
        # Get all appointments for today
        today_appointments = Appointment.objects.filter(
            doctor=doctor,
            scheduled_start__date=target_date
        ).order_by('scheduled_start')
        
        # Count by status
        status_counts = {}
        for status_choice in Appointment.Status.choices:
            status_counts[status_choice[0]] = today_appointments.filter(status=status_choice[0]).count()
        
        # Get next appointment
        next_appointment = today_appointments.filter(
            status__in=[Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN]
        ).order_by('scheduled_start').first()
        
        # Get currently being seen (checked in but not completed)
        current_appointment = today_appointments.filter(
            status=Appointment.Status.CHECKED_IN
        ).order_by('checked_in_by').first()
        
        return {
            'date': target_date,
            'total_appointments': today_appointments.count(),
            'status_counts': status_counts,
            'next_appointment': next_appointment,
            'current_appointment': current_appointment,
            'appointments': list(today_appointments)
        }
    
    @staticmethod
    def get_queue_statistics(doctor: DoctorProfile, date_range: int = 7) -> dict:
        """
        Get queue statistics for a doctor over a date range
        
        Args:
            doctor: Doctor profile to get statistics for
            date_range: Number of days to look back
            
        Returns:
            Dictionary with queue statistics
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=date_range)
        
        # Get appointments in date range
        appointments = Appointment.objects.filter(
            doctor=doctor,
            scheduled_start__date__gte=start_date,
            scheduled_start__date__lte=end_date
        )
        
        # Calculate statistics
        total_appointments = appointments.count()
        completed_appointments = appointments.filter(status=Appointment.Status.COMPLETED).count()
        cancelled_appointments = appointments.filter(status=Appointment.Status.CANCELLED).count()
        no_show_appointments = appointments.filter(status=Appointment.Status.NO_SHOW).count()
        
        # Calculate average waiting time for completed appointments
        waiting_times = []
        for appointment in appointments.filter(status=Appointment.Status.COMPLETED):
            check_in_time = QueueManagementService._get_check_in_time(appointment)
            if check_in_time:
                # Find completion time from status history
                from apps.appointments.models import AppointmentStatusHistory
                completion_time = AppointmentStatusHistory.objects.filter(
                    appointment=appointment,
                    new_status=Appointment.Status.COMPLETED
                ).order_by('created_at').first()
                
                if completion_time:
                    waiting_time = completion_time.created_at - check_in_time
                    waiting_times.append(waiting_time.total_seconds() / 60)  # Convert to minutes
        
        avg_waiting_time = sum(waiting_times) / len(waiting_times) if waiting_times else 0
        
        return {
            'date_range_days': date_range,
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'cancelled_appointments': cancelled_appointments,
            'no_show_appointments': no_show_appointments,
            'completion_rate': (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0,
            'cancellation_rate': (cancelled_appointments / total_appointments * 100) if total_appointments > 0 else 0,
            'no_show_rate': (no_show_appointments / total_appointments * 100) if total_appointments > 0 else 0,
            'average_waiting_time_minutes': round(avg_waiting_time, 2)
        }
    
    @staticmethod
    def get_overview_for_receptionist() -> dict:
        """
        Get queue overview for receptionists
        
        Returns:
            Dictionary with overall queue statistics
        """
        target_date = timezone.now().date()
        
        # Get all appointments for today
        today_appointments = Appointment.objects.filter(
            scheduled_start__date=target_date
        )
        
        # Count by status
        status_counts = {}
        for status_choice in Appointment.Status.choices:
            status_counts[status_choice[0]] = today_appointments.filter(status=status_choice[0]).count()
        
        # Get waiting room summary
        waiting_patients = today_appointments.filter(status=Appointment.Status.CHECKED_IN).count()
        
        # Get doctors with appointments today
        doctors_today = DoctorProfile.objects.filter(
            appointments__scheduled_start__date=target_date
        ).distinct()
        
        doctor_summaries = []
        for doctor in doctors_today:
            doctor_schedule = QueueManagementService.get_today_schedule(doctor)
            doctor_summaries.append({
                'doctor': doctor,
                'total_appointments': doctor_schedule['total_appointments'],
                'checked_in': doctor_schedule['status_counts'].get('CHECKED_IN', 0),
                'confirmed': doctor_schedule['status_counts'].get('CONFIRMED', 0),
                'completed': doctor_schedule['status_counts'].get('COMPLETED', 0),
                'current_appointment': doctor_schedule['current_appointment']
            })
        
        return {
            'date': target_date,
            'total_appointments': today_appointments.count(),
            'status_counts': status_counts,
            'waiting_patients': waiting_patients,
            'doctor_summaries': doctor_summaries
        }
    
    @staticmethod
    def estimate_wait_time(doctor: DoctorProfile) -> Optional[int]:
        """
        Estimate wait time for a new patient
        
        Args:
            doctor: Doctor profile to estimate wait time for
            
        Returns:
            Estimated wait time in minutes, or None if cannot estimate
        """
        target_date = timezone.now().date()
        
        # Get checked-in patients ahead in queue
        checked_in_count = Appointment.objects.filter(
            doctor=doctor,
            scheduled_start__date=target_date,
            status=Appointment.Status.CHECKED_IN
        ).count()
        
        # Get confirmed patients who haven't checked in yet
        confirmed_count = Appointment.objects.filter(
            doctor=doctor,
            scheduled_start__date=target_date,
            status=Appointment.Status.CONFIRMED,
            scheduled_start__gt=timezone.now()
        ).count()
        
        if checked_in_count == 0:
            return None  # No queue
        
        # Estimate based on doctor's consultation duration
        avg_consultation_time = doctor.consultation_duration_minutes
        
        # Add buffer time
        total_buffer = (checked_in_count + confirmed_count) * (doctor.buffer_before_minutes + doctor.buffer_after_minutes)
        
        estimated_wait = (checked_in_count * avg_consultation_time) + total_buffer
        
        return max(estimated_wait, avg_consultation_time)  # At least one consultation time
