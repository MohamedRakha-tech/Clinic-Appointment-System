from datetime import datetime, timedelta, time, date
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.accounts.models import PatientProfile, DoctorProfile, ReceptionistProfile, AdminProfile
from apps.appointments.models import Appointment, AppointmentStatusHistory, AppointmentRescheduleHistory
from apps.scheduling.models import DoctorWeeklySchedule, AppointmentSlot
from apps.appointments.services import (
    AppointmentBookingService, AppointmentStatusService, 
    AppointmentRescheduleService, AppointmentOverlapService
)
from apps.scheduling.services import SlotGenerationService
from apps.queueing.services import QueueManagementService

User = get_user_model()


class AppointmentBookingTestCase(TestCase):
    """Test appointment booking functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='test123'
        )
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor@test.com', password='test123'
        )
        
        # Create profiles
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 1, 1)
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Practice',
            license_number='DOC123',
            consultation_duration_minutes=15,
            buffer_before_minutes=5,
            buffer_after_minutes=5
        )
        
        # Create weekly schedule
        self.weekly_schedule = DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=0,  # Monday
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        
        # Create appointment slot
        slot_datetime = timezone.make_aware(datetime(2024, 1, 15, 9, 0))  # Monday 9 AM
        self.slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=slot_datetime,
            end_datetime=slot_datetime + timedelta(minutes=15),
            status=AppointmentSlot.Status.AVAILABLE
        )
    
    def test_successful_appointment_booking(self):
        """Test successful appointment booking"""
        appointment, success = AppointmentBookingService.book_appointment(
            patient=self.patient,
            doctor=self.doctor,
            slot=self.slot
        )
        
        self.assertTrue(success)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.doctor, self.doctor)
        self.assertEqual(appointment.slot, self.slot)
        self.assertEqual(appointment.status, Appointment.Status.REQUESTED)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, AppointmentSlot.Status.BOOKED)
    
    def test_double_booking_prevention(self):
        """Test that double booking is prevented"""
        # Book first appointment
        AppointmentBookingService.book_appointment(
            patient=self.patient,
            doctor=self.doctor,
            slot=self.slot
        )
        
        # Try to book same slot again
        with self.assertRaises(ValidationError) as context:
            AppointmentBookingService.book_appointment(
                patient=self.patient,
                doctor=self.doctor,
                slot=self.slot
            )
        
        self.assertIn("not available for booking", str(context.exception))
    
    def test_patient_overlap_prevention(self):
        """Test that patient cannot book overlapping appointments"""
        # Create another slot at overlapping time
        overlapping_datetime = timezone.make_aware(datetime(2024, 1, 15, 9, 10))
        overlapping_slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=overlapping_datetime,
            end_datetime=overlapping_datetime + timedelta(minutes=15),
            status=AppointmentSlot.Status.AVAILABLE
        )
        
        # Book first appointment
        AppointmentBookingService.book_appointment(
            patient=self.patient,
            doctor=self.doctor,
            slot=self.slot
        )
        
        # Try to book overlapping appointment
        with self.assertRaises(ValidationError) as context:
            AppointmentBookingService.book_appointment(
                patient=self.patient,
                doctor=self.doctor,
                slot=overlapping_slot
            )
        
        self.assertIn("overlapping appointment", str(context.exception))


class AppointmentStatusTestCase(TestCase):
    """Test appointment status transitions"""
    
    def setUp(self):
        """Set up test data"""
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='test123'
        )
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor@test.com', password='test123'
        )
        self.receptionist_user = User.objects.create_user(
            username='receptionist1', email='receptionist@test.com', password='test123'
        )
        
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 1, 1)
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Practice',
            license_number='DOC123'
        )
        self.receptionist = ReceptionistProfile.objects.create(
            user=self.receptionist_user,
            employee_code='REC001'
        )
        
        # Create appointment
        slot_datetime = timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=slot_datetime,
            end_datetime=slot_datetime + timedelta(minutes=15),
            status=AppointmentSlot.Status.BOOKED
        )
        
        self.appointment = Appointment.objects.create(
            appointment_code='APT123456',
            patient=self.patient,
            doctor=self.doctor,
            slot=slot,
            scheduled_start=slot_datetime,
            scheduled_end=slot_datetime + timedelta(minutes=15),
            status=Appointment.Status.REQUESTED
        )
    
    def test_patient_can_cancel_own_appointment(self):
        """Test that patient can cancel their own appointment"""
        updated_appointment, success = AppointmentStatusService.update_appointment_status(
            appointment=self.appointment,
            new_status=Appointment.Status.CANCELLED,
            changed_by=self.patient_user,
            reason="Patient cancelled"
        )
        
        self.assertTrue(success)
        self.assertEqual(updated_appointment.status, Appointment.Status.CANCELLED)
        self.assertEqual(updated_appointment.cancelled_by, self.patient_user)
    
    def test_patient_cannot_cancel_other_appointment(self):
        """Test that patient cannot cancel other's appointment"""
        other_patient_user = User.objects.create_user(
            username='patient2', email='patient2@test.com', password='test123'
        )
        
        with self.assertRaises(ValidationError) as context:
            AppointmentStatusService.update_appointment_status(
                appointment=self.appointment,
                new_status=Appointment.Status.CANCELLED,
                changed_by=other_patient_user
            )
        
        self.assertIn("can only cancel own appointments", str(context.exception))
    
    def test_doctor_can_confirm_appointment(self):
        """Test that doctor can confirm appointment"""
        updated_appointment, success = AppointmentStatusService.update_appointment_status(
            appointment=self.appointment,
            new_status=Appointment.Status.CONFIRMED,
            changed_by=self.doctor_user
        )
        
        self.assertTrue(success)
        self.assertEqual(updated_appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(updated_appointment.confirmed_by, self.doctor_user)
    
    def test_invalid_status_transition(self):
        """Test that invalid status transitions are prevented"""
        with self.assertRaises(ValidationError) as context:
            AppointmentStatusService.update_appointment_status(
                appointment=self.appointment,
                new_status=Appointment.Status.COMPLETED,  # Can't go directly to COMPLETED
                changed_by=self.doctor_user
            )
        
        self.assertIn("Invalid status transition", str(context.exception))


class SlotGenerationTestCase(TestCase):
    """Test slot generation functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor@test.com', password='test123'
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Practice',
            license_number='DOC123',
            consultation_duration_minutes=15,
            buffer_before_minutes=5,
            buffer_after_minutes=5
        )
        
        # Create weekly schedule
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=0,  # Monday
            start_time=time(9, 0),
            end_time=time(11, 0)  # 2 hours
        )
    
    def test_slot_generation_with_buffer_time(self):
        """Test slot generation respects buffer time"""
        start_date = date(2024, 1, 15)  # Monday
        end_date = date(2024, 1, 15)
        
        slots = SlotGenerationService.generate_slots_for_date_range(
            doctor=self.doctor,
            start_date=start_date,
            end_date=end_date
        )
        
        # Should generate 4 slots in 2 hours with 15 min consultation + 10 min buffer
        # 9:00-9:25, 9:25-9:50, 9:50-10:15, 10:15-10:40
        self.assertEqual(len(slots), 4)
        
        # Check first slot timing
        first_slot = slots[0]
        expected_start = timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        expected_end = timezone.make_aware(datetime(2024, 1, 15, 9, 25))  # 15 min + 5 min before + 5 min after
        self.assertEqual(first_slot.start_datetime, expected_start)
        self.assertEqual(first_slot.end_datetime, expected_end)
    
    def test_buffer_time_enforcement(self):
        """Test that buffer time is properly enforced"""
        # Create a slot
        slot_datetime = timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=slot_datetime,
            end_datetime=slot_datetime + timedelta(minutes=25),  # Includes buffer
            status=AppointmentSlot.Status.AVAILABLE
        )
        
        # Create overlapping appointment (should be prevented)
        overlapping_datetime = timezone.make_aware(datetime(2024, 1, 15, 9, 10))
        overlapping_slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=overlapping_datetime,
            end_datetime=overlapping_datetime + timedelta(minutes=25),
            status=AppointmentSlot.Status.AVAILABLE
        )
        
        patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='test123'
        )
        patient = PatientProfile.objects.create(
            user=patient_user,
            date_of_birth=date(1990, 1, 1)
        )
        
        # Book first appointment
        AppointmentBookingService.book_appointment(
            patient=patient,
            doctor=self.doctor,
            slot=slot
        )
        
        # Try to book overlapping appointment (should fail)
        with self.assertRaises(ValidationError):
            AppointmentBookingService.book_appointment(
                patient=patient,
                doctor=self.doctor,
                slot=overlapping_slot
            )


class AppointmentRescheduleTestCase(TestCase):
    """Test appointment rescheduling functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='test123'
        )
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor@test.com', password='test123'
        )
        
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 1, 1)
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Practice',
            license_number='DOC123'
        )
        
        # Create original slot and appointment
        original_slot_datetime = timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        self.original_slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=original_slot_datetime,
            end_datetime=original_slot_datetime + timedelta(minutes=15),
            status=AppointmentSlot.Status.BOOKED
        )
        
        self.appointment = Appointment.objects.create(
            appointment_code='APT123456',
            patient=self.patient,
            doctor=self.doctor,
            slot=self.original_slot,
            scheduled_start=original_slot_datetime,
            scheduled_end=original_slot_datetime + timedelta(minutes=15),
            status=Appointment.Status.CONFIRMED
        )
        
        # Create new slot for rescheduling
        new_slot_datetime = timezone.make_aware(datetime(2024, 1, 15, 10, 0))
        self.new_slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=new_slot_datetime,
            end_datetime=new_slot_datetime + timedelta(minutes=15),
            status=AppointmentSlot.Status.AVAILABLE
        )
    
    def test_successful_rescheduling(self):
        """Test successful appointment rescheduling"""
        updated_appointment, success = AppointmentRescheduleService.reschedule_appointment(
            appointment=self.appointment,
            new_slot_id=self.new_slot.id,
            reason="Patient requested different time",
            changed_by=self.patient_user
        )
        
        self.assertTrue(success)
        self.assertEqual(updated_appointment.slot, self.new_slot)
        self.assertEqual(updated_appointment.scheduled_start, self.new_slot.start_datetime)
        
        # Check audit trail
        reschedule_history = AppointmentRescheduleHistory.objects.filter(
            appointment=self.appointment
        ).first()
        self.assertIsNotNone(reschedule_history)
        self.assertEqual(reschedule_history.reason, "Patient requested different time")
        self.assertEqual(reschedule_history.changed_by, self.patient_user)
        
        # Check slot statuses
        self.original_slot.refresh_from_db()
        self.new_slot.refresh_from_db()
        self.assertEqual(self.original_slot.status, AppointmentSlot.Status.AVAILABLE)
        self.assertEqual(self.new_slot.status, AppointmentSlot.Status.BOOKED)
    
    def test_rescheduling_different_doctor_prevention(self):
        """Test that rescheduling to different doctor is prevented"""
        other_doctor_user = User.objects.create_user(
            username='doctor2', email='doctor2@test.com', password='test123'
        )
        other_doctor = DoctorProfile.objects.create(
            user=other_doctor_user,
            specialization='Cardiology',
            license_number='DOC456'
        )
        
        # Create slot for different doctor
        different_doctor_slot = AppointmentSlot.objects.create(
            doctor=other_doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=timezone.make_aware(datetime(2024, 1, 15, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2024, 1, 15, 10, 15)),
            status=AppointmentSlot.Status.AVAILABLE
        )
        
        with self.assertRaises(ValidationError) as context:
            AppointmentRescheduleService.reschedule_appointment(
                appointment=self.appointment,
                new_slot_id=different_doctor_slot.id,
                reason="Want different doctor",
                changed_by=self.patient_user
            )
        
        self.assertIn("must belong to the same doctor", str(context.exception))


class QueueManagementTestCase(TestCase):
    """Test queue management functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor@test.com', password='test123'
        )
        self.receptionist_user = User.objects.create_user(
            username='receptionist1', email='receptionist@test.com', password='test123'
        )
        
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Practice',
            license_number='DOC123'
        )
        
        # Create multiple appointments for today
        today = timezone.now().date()
        for i in range(3):
            patient_user = User.objects.create_user(
                username=f'patient{i}', email=f'patient{i}@test.com', password='test123'
            )
            patient = PatientProfile.objects.create(
                user=patient_user,
                date_of_birth=date(1990, 1, 1)
            )
            
            slot_datetime = timezone.make_aware(datetime.combine(today, time(9 + i, 0)))
            slot = AppointmentSlot.objects.create(
                doctor=self.doctor,
                slot_date=today,
                start_datetime=slot_datetime,
                end_datetime=slot_datetime + timedelta(minutes=15),
                status=AppointmentSlot.Status.BOOKED
            )
            
            Appointment.objects.create(
                appointment_code=f'APT{i}23456',
                patient=patient,
                doctor=self.doctor,
                slot=slot,
                scheduled_start=slot_datetime,
                scheduled_end=slot_datetime + timedelta(minutes=15),
                status=Appointment.Status.CONFIRMED if i < 2 else Appointment.Status.CHECKED_IN
            )
    
    def test_get_doctor_queue(self):
        """Test getting doctor queue"""
        queue = QueueManagementService.get_doctor_queue(self.doctor)
        
        self.assertEqual(len(queue), 3)
        # Should be ordered by scheduled_start
        self.assertTrue(queue[0].scheduled_start < queue[1].scheduled_start < queue[2].scheduled_start)
    
    def test_patient_check_in(self):
        """Test patient check-in functionality"""
        appointment = Appointment.objects.filter(status=Appointment.Status.CONFIRMED).first()
        
        checked_in_appointment, success = QueueManagementService.check_in_patient(
            appointment=appointment,
            checked_in_by=self.receptionist_user
        )
        
        self.assertTrue(success)
        self.assertEqual(checked_in_appointment.status, Appointment.Status.CHECKED_IN)
        self.assertEqual(checked_in_appointment.checked_in_by, self.receptionist_user)
    
    def test_waiting_room_queue(self):
        """Test getting waiting room queue"""
        waiting_queue = QueueManagementService.get_waiting_room_queue(self.doctor)
        
        # Should have one checked-in patient
        self.assertEqual(len(waiting_queue), 1)
        self.assertIn('waiting_time_minutes', waiting_queue[0])
        self.assertIn('patient_name', waiting_queue[0])


class PermissionTestCase(TestCase):
    """Test role-based permissions"""
    
    def setUp(self):
        """Set up test data with different user roles"""
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='test123'
        )
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor@test.com', password='test123'
        )
        self.receptionist_user = User.objects.create_user(
            username='receptionist1', email='receptionist@test.com', password='test123'
        )
        self.admin_user = User.objects.create_user(
            username='admin1', email='admin@test.com', password='test123'
        )
        
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 1, 1)
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Practice',
            license_number='DOC123'
        )
        self.receptionist = ReceptionistProfile.objects.create(
            user=self.receptionist_user,
            employee_code='REC001'
        )
        self.admin = AdminProfile.objects.create(
            user=self.admin_user,
            employee_code='ADM001'
        )
        
        # Create appointment
        slot_datetime = timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=slot_datetime,
            end_datetime=slot_datetime + timedelta(minutes=15),
            status=AppointmentSlot.Status.BOOKED
        )
        
        self.appointment = Appointment.objects.create(
            appointment_code='APT123456',
            patient=self.patient,
            doctor=self.doctor,
            slot=slot,
            scheduled_start=slot_datetime,
            scheduled_end=slot_datetime + timedelta(minutes=15),
            status=Appointment.Status.CONFIRMED
        )
    
    def test_patient_reschedule_permissions(self):
        """Test patient rescheduling permissions"""
        # Patient can reschedule their own confirmed appointment
        can_reschedule = AppointmentRescheduleService.can_reschedule(
            self.appointment, self.patient_user
        )
        self.assertTrue(can_reschedule)
        
        # Patient cannot reschedule if status is not REQUESTED or CONFIRMED
        self.appointment.status = Appointment.Status.CHECKED_IN
        self.appointment.save()
        can_reschedule = AppointmentRescheduleService.can_reschedule(
            self.appointment, self.patient_user
        )
        self.assertFalse(can_reschedule)
    
    def test_doctor_cannot_reschedule(self):
        """Test that doctors cannot reschedule appointments"""
        can_reschedule = AppointmentRescheduleService.can_reschedule(
            self.appointment, self.doctor_user
        )
        self.assertFalse(can_reschedule)
    
    def test_receptionist_can_reschedule_any(self):
        """Test that receptionists can reschedule any appointment"""
        can_reschedule = AppointmentRescheduleService.can_reschedule(
            self.appointment, self.receptionist_user
        )
        self.assertTrue(can_reschedule)
    
    def test_admin_can_reschedule_any(self):
        """Test that admins can reschedule any appointment"""
        can_reschedule = AppointmentRescheduleService.can_reschedule(
            self.appointment, self.admin_user
        )
        self.assertTrue(can_reschedule)


class OverlapDetectionTestCase(TestCase):
    """Test overlap detection functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='test123'
        )
        self.doctor_user = User.objects.create_user(
            username='doctor1', email='doctor@test.com', password='test123'
        )
        
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            date_of_birth=date(1990, 1, 1)
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            specialization='General Practice',
            license_number='DOC123'
        )
    
    def test_doctor_availability_check(self):
        """Test doctor availability checking"""
        # Create existing appointment
        existing_start = timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        existing_end = timezone.make_aware(datetime(2024, 1, 15, 9, 30))
        
        slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=existing_start,
            end_datetime=existing_end,
            status=AppointmentSlot.Status.BOOKED
        )
        
        Appointment.objects.create(
            appointment_code='APT123456',
            patient=self.patient,
            doctor=self.doctor,
            slot=slot,
            scheduled_start=existing_start,
            scheduled_end=existing_end,
            status=Appointment.Status.CONFIRMED
        )
        
        # Test overlapping time
        is_available = AppointmentOverlapService.check_doctor_availability(
            doctor=self.doctor,
            start_time=timezone.make_aware(datetime(2024, 1, 15, 9, 15)),
            end_time=timezone.make_aware(datetime(2024, 1, 15, 9, 45))
        )
        self.assertFalse(is_available)
        
        # Test non-overlapping time
        is_available = AppointmentOverlapService.check_doctor_availability(
            doctor=self.doctor,
            start_time=timezone.make_aware(datetime(2024, 1, 15, 10, 0)),
            end_time=timezone.make_aware(datetime(2024, 1, 15, 10, 30))
        )
        self.assertTrue(is_available)
    
    def test_patient_availability_check(self):
        """Test patient availability checking"""
        # Create existing appointment
        existing_start = timezone.make_aware(datetime(2024, 1, 15, 9, 0))
        existing_end = timezone.make_aware(datetime(2024, 1, 15, 9, 30))
        
        slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=date(2024, 1, 15),
            start_datetime=existing_start,
            end_datetime=existing_end,
            status=AppointmentSlot.Status.BOOKED
        )
        
        existing_appointment = Appointment.objects.create(
            appointment_code='APT123456',
            patient=self.patient,
            doctor=self.doctor,
            slot=slot,
            scheduled_start=existing_start,
            scheduled_end=existing_end,
            status=Appointment.Status.CONFIRMED
        )
        
        # Test overlapping time
        is_available = AppointmentOverlapService.check_patient_availability(
            patient=self.patient,
            start_time=timezone.make_aware(datetime(2024, 1, 15, 9, 15)),
            end_time=timezone.make_aware(datetime(2024, 1, 15, 9, 45)),
            exclude_appointment_id=existing_appointment.id
        )
        self.assertFalse(is_available)
        
        # Test non-overlapping time
        is_available = AppointmentOverlapService.check_patient_availability(
            patient=self.patient,
            start_time=timezone.make_aware(datetime(2024, 1, 15, 10, 0)),
            end_time=timezone.make_aware(datetime(2024, 1, 15, 10, 30)),
            exclude_appointment_id=existing_appointment.id
        )
        self.assertTrue(is_available)
