from datetime import datetime, timedelta
from typing import Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.accounts.models import User, PatientProfile, DoctorProfile
from apps.appointments.models import Appointment, AppointmentStatusHistory, AppointmentRescheduleHistory
from apps.scheduling.models import AppointmentSlot
from apps.scheduling.services import SlotGenerationService


class AppointmentBookingService:
    """Service for handling appointment bookings with transaction safety"""
    
    @staticmethod
    @transaction.atomic
    def book_appointment(
        patient: PatientProfile,
        doctor: DoctorProfile,
        slot: AppointmentSlot,
        booking_source: str = Appointment.BookingSource.PATIENT,
        notes_for_staff: Optional[str] = None,
        booked_by: Optional[User] = None
    ) -> Tuple[Appointment, bool]:
        """
        Book an appointment with transaction safety and conflict prevention
        
        Args:
            patient: Patient profile booking the appointment
            doctor: Doctor profile for the appointment
            slot: Appointment slot to book
            booking_source: Source of booking (PATIENT, RECEPTIONIST, ADMIN)
            notes_for_staff: Optional notes for staff
            booked_by: User who made the booking (if different from patient)
            
        Returns:
            Tuple of (Appointment instance, success boolean)
            
        Raises:
            ValidationError: If booking rules are violated
        """
        # Validate slot availability
        if not SlotGenerationService.check_slot_availability(slot):
            raise ValidationError("Slot is not available for booking")
        
        # Check for patient overlapping appointments
        if AppointmentBookingService._has_patient_conflict(
            patient, slot.start_datetime, slot.end_datetime
        ):
            raise ValidationError("Patient has an overlapping appointment")
        
        # Generate appointment code
        appointment_code = AppointmentBookingService._generate_appointment_code()
        
        # Create appointment
        appointment = Appointment.objects.create(
            appointment_code=appointment_code,
            patient=patient,
            doctor=doctor,
            slot=slot,
            scheduled_start=slot.start_datetime,
            scheduled_end=slot.end_datetime,
            status=Appointment.Status.REQUESTED,
            booking_source=booking_source,
            notes_for_staff=notes_for_staff
        )
        
        # Mark slot as booked
        SlotGenerationService.mark_slot_booked(slot)
        
        # Record status change
        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            old_status=None,
            new_status=Appointment.Status.REQUESTED,
            changed_by=booked_by or patient.user
        )
        
        return appointment, True
    
    @staticmethod
    def _has_patient_conflict(
        patient: PatientProfile,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """Check if patient has overlapping appointments"""
        conflicting_appointments = Appointment.objects.filter(
            patient=patient,
            status__in=[Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED, 
                       Appointment.Status.CHECKED_IN],
        ).filter(
            scheduled_start__lt=end_time,
            scheduled_end__gt=start_time
        ).exists()
        
        return conflicting_appointments
    
    @staticmethod
    def _generate_appointment_code() -> str:
        """Generate unique appointment code"""
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Appointment.objects.filter(appointment_code=code).exists():
                return code


class AppointmentStatusService:
    """Service for handling appointment status transitions"""
    
    @staticmethod
    @transaction.atomic
    def update_appointment_status(
        appointment: Appointment,
        new_status: str,
        changed_by: User,
        reason: Optional[str] = None
    ) -> Tuple[Appointment, bool]:
        """
        Update appointment status with validation and audit trail
        
        Args:
            appointment: Appointment to update
            new_status: New status value
            changed_by: User making the change
            reason: Optional reason for status change
            
        Returns:
            Tuple of (updated Appointment, success boolean)
            
        Raises:
            ValidationError: If status transition is invalid
        """
        old_status = appointment.status
        
        # Validate status transition
        AppointmentStatusService._validate_status_transition(
            old_status, new_status, changed_by, appointment
        )
        
        # Update appointment status
        appointment.status = new_status
        appointment.updated_at = timezone.now()
        
        # Set specific fields based on status
        if new_status == Appointment.Status.CONFIRMED:
            appointment.confirmed_by = changed_by
        elif new_status == Appointment.Status.CHECKED_IN:
            appointment.checked_in_by = changed_by
        elif new_status == Appointment.Status.CANCELLED:
            appointment.cancelled_by = changed_by
            appointment.cancellation_reason = reason
            # Release the slot
            SlotGenerationService.release_slot(appointment.slot)
        
        appointment.save()
        
        # Record status change
        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            change_reason=reason
        )
        
        return appointment, True
    
    @staticmethod
    def _validate_status_transition(
        old_status: str,
        new_status: str,
        changed_by: User,
        appointment: Appointment
    ) -> None:
        """Validate if status transition is allowed for the user"""
        
        # Define allowed transitions
        allowed_transitions = {
            Appointment.Status.REQUESTED: [
                Appointment.Status.CONFIRMED,
                Appointment.Status.CANCELLED,
                Appointment.Status.NO_SHOW
            ],
            Appointment.Status.CONFIRMED: [
                Appointment.Status.CHECKED_IN,
                Appointment.Status.CANCELLED,
                Appointment.Status.NO_SHOW
            ],
            Appointment.Status.CHECKED_IN: [
                Appointment.Status.COMPLETED,
                Appointment.Status.NO_SHOW
            ],
            Appointment.Status.COMPLETED: [],  # Terminal state
            Appointment.Status.CANCELLED: [],   # Terminal state
            Appointment.Status.NO_SHOW: [],     # Terminal state
        }
        
        if new_status not in allowed_transitions.get(old_status, []):
            raise ValidationError(f"Invalid status transition from {old_status} to {new_status}")
        
        # Check user permissions for specific transitions
        user_role = AppointmentStatusService._get_user_role(changed_by)
        
        # Patients can only cancel their own appointments (REQUESTED or CONFIRMED)
        if user_role == 'patient':
            if new_status != Appointment.Status.CANCELLED:
                raise ValidationError("Patients can only cancel appointments")
            if old_status not in [Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED]:
                raise ValidationError("Can only cancel REQUESTED or CONFIRMED appointments")
            if appointment.patient.user != changed_by:
                raise ValidationError("Can only cancel own appointments")
        
        # Only doctors can check-in patients
        elif user_role == 'doctor':
            if new_status == Appointment.Status.CHECKED_IN:
                if appointment.doctor.user != changed_by:
                    raise ValidationError("Only assigned doctor can check-in patient")
            elif new_status not in [Appointment.Status.CONFIRMED, Appointment.Status.CANCELLED, 
                                   Appointment.Status.NO_SHOW]:
                raise ValidationError("Doctor cannot perform this status change")
        
        # Receptionists can confirm, check-in, cancel, and mark no-show
        elif user_role == 'receptionist':
            if new_status not in [Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN,
                                 Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW]:
                raise ValidationError("Receptionist cannot perform this status change")
        
        # Admins can do anything (within allowed transitions)
        # No additional checks needed for admin
    
    @staticmethod
    def _get_user_role(user: User) -> str:
        """Get user role based on profile"""
        if hasattr(user, 'patient_profile'):
            return 'patient'
        elif hasattr(user, 'doctor_profile'):
            return 'doctor'
        elif hasattr(user, 'receptionist_profile'):
            return 'receptionist'
        elif hasattr(user, 'admin_profile'):
            return 'admin'
        else:
            return 'unknown'


class AppointmentOverlapService:
    """Service for checking appointment overlaps"""
    
    @staticmethod
    def check_doctor_availability(
        doctor: DoctorProfile,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: Optional[int] = None
    ) -> bool:
        """Check if doctor is available during the time slot"""
        queryset = Appointment.objects.filter(
            doctor=doctor,
            status__in=[Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED, 
                       Appointment.Status.CHECKED_IN],
        ).filter(
            scheduled_start__lt=end_time,
            scheduled_end__gt=start_time
        )
        
        if exclude_appointment_id:
            queryset = queryset.exclude(id=exclude_appointment_id)
        
        return not queryset.exists()
    
    @staticmethod
    def check_patient_availability(
        patient: PatientProfile,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: Optional[int] = None
    ) -> bool:
        """Check if patient is available during the time slot"""
        queryset = Appointment.objects.filter(
            patient=patient,
            status__in=[Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED, 
                       Appointment.Status.CHECKED_IN],
        ).filter(
            scheduled_start__lt=end_time,
            scheduled_end__gt=start_time
        )
        
        if exclude_appointment_id:
            queryset = queryset.exclude(id=exclude_appointment_id)
        
        return not queryset.exists()


class AppointmentRescheduleService:
    """Service for handling appointment rescheduling with audit trail"""
    
    @staticmethod
    @transaction.atomic
    def reschedule_appointment(
        appointment: Appointment,
        new_slot_id: int,
        reason: str,
        changed_by: User
    ) -> Tuple[Appointment, bool]:
        """
        Reschedule an appointment with complete audit trail
        
        Args:
            appointment: Appointment to reschedule
            new_slot_id: ID of the new slot
            reason: Reason for rescheduling
            changed_by: User making the change
            
        Returns:
            Tuple of (updated Appointment, success boolean)
            
        Raises:
            ValidationError: If rescheduling rules are violated
        """
        from apps.scheduling.models import AppointmentSlot
        from apps.scheduling.services import SlotGenerationService
        
        # Get the new slot
        try:
            new_slot = AppointmentSlot.objects.get(id=new_slot_id)
        except AppointmentSlot.DoesNotExist:
            raise ValidationError("New slot does not exist")
        
        # Validate new slot is available
        if not SlotGenerationService.check_slot_availability(new_slot):
            raise ValidationError("New slot is not available")
        
        # Validate new slot belongs to the same doctor
        if new_slot.doctor != appointment.doctor:
            raise ValidationError("New slot must belong to the same doctor")
        
        # Check for patient overlapping appointments (excluding current appointment)
        if not AppointmentOverlapService.check_patient_availability(
            appointment.patient, new_slot.start_datetime, new_slot.end_datetime, appointment.id
        ):
            raise ValidationError("Patient has an overlapping appointment with the new slot")
        
        # Store old slot information for audit trail
        old_slot = appointment.slot
        old_start = appointment.scheduled_start
        old_end = appointment.scheduled_end
        
        # Update appointment with new slot
        appointment.slot = new_slot
        appointment.scheduled_start = new_slot.start_datetime
        appointment.scheduled_end = new_slot.end_datetime
        appointment.updated_at = timezone.now()
        appointment.save()
        
        # Mark new slot as booked
        SlotGenerationService.mark_slot_booked(new_slot)
        
        # Release old slot
        SlotGenerationService.release_slot(old_slot)
        
        # Create reschedule history record
        AppointmentRescheduleHistory.objects.create(
            appointment=appointment,
            old_start_datetime=old_start,
            old_end_datetime=old_end,
            new_start_datetime=new_slot.start_datetime,
            new_end_datetime=new_slot.end_datetime,
            changed_by=changed_by,
            reason=reason
        )
        
        return appointment, True
    
    @staticmethod
    def get_reschedule_history(appointment: Appointment) -> AppointmentRescheduleHistory:
        """Get reschedule history for an appointment"""
        return appointment.reschedule_history.all().order_by('created_at')
    
    @staticmethod
    def can_reschedule(appointment: Appointment, user: User) -> bool:
        """Check if user can reschedule the appointment"""
        # Patients can reschedule their own appointments (REQUESTED/CONFIRMED)
        if hasattr(user, 'patient_profile'):
            if appointment.patient.user != user:
                return False
            return appointment.status in [Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED]
        
        # Receptionist and admin can reschedule any appointment
        if hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile'):
            return True
        
        # Doctors cannot reschedule (they can only manage status)
        return False
