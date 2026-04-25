from datetime import datetime, timedelta, time, date
from typing import List, Optional
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import DoctorProfile
from apps.scheduling.models import DoctorWeeklySchedule, DoctorScheduleException, AppointmentSlot


class SlotGenerationService:
    """Service for generating appointment slots with buffer time handling"""
    
    @staticmethod
    def generate_slots_for_date_range(
        doctor: DoctorProfile,
        start_date: date,
        end_date: date,
        regenerate: bool = False
    ) -> List[AppointmentSlot]:
        """
        Generate appointment slots for a doctor within a date range.
        
        Args:
            doctor: Doctor profile to generate slots for
            start_date: Start date for slot generation
            end_date: End date for slot generation
            regenerate: If True, delete existing slots before generating new ones
            
        Returns:
            List of generated AppointmentSlot objects
        """
        if regenerate:
            AppointmentSlot.objects.filter(
                doctor=doctor,
                slot_date__gte=start_date,
                slot_date__lte=end_date
            ).delete()
        
        generated_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            daily_slots = SlotGenerationService._generate_slots_for_single_day(
                doctor, current_date
            )
            generated_slots.extend(daily_slots)
            current_date += timedelta(days=1)
        
        return generated_slots
    
    @staticmethod
    def _generate_slots_for_single_day(doctor: DoctorProfile, target_date: date) -> List[AppointmentSlot]:
        """Generate slots for a single day considering weekly schedule and exceptions"""
        
        # Check for schedule exceptions
        exception = SlotGenerationService._get_schedule_exception(doctor, target_date)
        
        if exception and exception.type == DoctorScheduleException.ExceptionType.DAY_OFF:
            return []
        
        if exception and exception.type == DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY:
            # Use exception times
            start_time = exception.start_time
            end_time = exception.end_time
            generated_from = AppointmentSlot.GeneratedFrom.EXCEPTION
        else:
            # Use weekly schedule
            weekly_schedule = SlotGenerationService._get_weekly_schedule(doctor, target_date)
            if not weekly_schedule:
                return []
            
            start_time = weekly_schedule.start_time
            end_time = weekly_schedule.end_time
            generated_from = AppointmentSlot.GeneratedFrom.WEEKLY_SCHEDULE
        
        # Generate slots with buffer times
        slots = SlotGenerationService._create_time_slots(
            doctor, target_date, start_time, end_time, generated_from
        )
        
        return slots
    
    @staticmethod
    def _get_schedule_exception(doctor: DoctorProfile, target_date: date) -> Optional[DoctorScheduleException]:
        """Get schedule exception for a specific date"""
        try:
            return DoctorScheduleException.objects.get(
                doctor=doctor,
                exception_date=target_date
            )
        except DoctorScheduleException.DoesNotExist:
            return None
    
    @staticmethod
    def _get_weekly_schedule(doctor: DoctorProfile, target_date: date) -> Optional[DoctorWeeklySchedule]:
        """Get weekly schedule for a specific day of week"""
        day_of_week = target_date.weekday()
        try:
            return DoctorWeeklySchedule.objects.get(
                doctor=doctor,
                day_of_week=day_of_week,
                is_active=True
            )
        except DoctorWeeklySchedule.DoesNotExist:
            return None
    
    @staticmethod
    def _create_time_slots(
        doctor: DoctorProfile,
        target_date: date,
        start_time: time,
        end_time: time,
        generated_from: str
    ) -> List[AppointmentSlot]:
        """Create time slots with buffer time considerations"""
        
        # Convert to datetime objects
        start_datetime = timezone.make_aware(
            datetime.combine(target_date, start_time)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(target_date, end_time)
        )
        
        # Calculate effective working hours (excluding buffer times)
        effective_start = start_datetime + timedelta(minutes=doctor.buffer_before_minutes)
        effective_end = end_datetime - timedelta(minutes=doctor.buffer_after_minutes)
        
        if effective_start >= effective_end:
            return []
        
        # Generate slots
        slots = []
        current_time = effective_start
        slot_duration = timedelta(minutes=doctor.consultation_duration_minutes)
        
        while current_time + slot_duration <= effective_end:
            slot_end = current_time + slot_duration
            
            # Create the slot with actual start/end times (including buffer)
            actual_start = current_time - timedelta(minutes=doctor.buffer_before_minutes)
            actual_end = slot_end + timedelta(minutes=doctor.buffer_after_minutes)
            
            # Ensure slot doesn't exceed working hours
            if actual_start < start_datetime:
                actual_start = start_datetime
            if actual_end > end_datetime:
                actual_end = end_datetime
            
            slot, created = AppointmentSlot.objects.get_or_create(
                doctor=doctor,
                start_datetime=actual_start,
                end_datetime=actual_end,
                defaults={
                    'slot_date': target_date,
                    'status': AppointmentSlot.Status.AVAILABLE,
                    'generated_from': generated_from
                }
            )
            
            if created:
                slots.append(slot)
            
            current_time = slot_end
        
        return slots
    
    @staticmethod
    def get_available_slots(
        doctor: DoctorProfile,
        start_date: date,
        end_date: date
    ) -> List[AppointmentSlot]:
        """Get available slots for a doctor within a date range"""
        return AppointmentSlot.objects.filter(
            doctor=doctor,
            slot_date__gte=start_date,
            slot_date__lte=end_date,
            status=AppointmentSlot.Status.AVAILABLE
        ).order_by('start_datetime')
    
    @staticmethod
    def check_slot_availability(slot: AppointmentSlot) -> bool:
        """Check if a slot is available for booking"""
        return slot.status == AppointmentSlot.Status.AVAILABLE
    
    @staticmethod
    def mark_slot_booked(slot: AppointmentSlot) -> bool:
        """Mark a slot as booked"""
        if SlotGenerationService.check_slot_availability(slot):
            slot.status = AppointmentSlot.Status.BOOKED
            slot.save()
            return True
        return False
    
    @staticmethod
    def release_slot(slot: AppointmentSlot) -> bool:
        """Release a booked slot back to available"""
        if slot.status == AppointmentSlot.Status.BOOKED:
            slot.status = AppointmentSlot.Status.AVAILABLE
            slot.save()
            return True
        return False
