# dashboard/tests/test_selectors.py

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import DoctorProfile, PatientProfile
from appointments.models import Appointment
from dashboard import selectors
from dashboard.models import AuditLog
from scheduling.models import AppointmentSlot

User = get_user_model()


class SelectorsTest(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor1',
            email='doctor@clinic.com',
            password='clinic1234',
            first_name='Ahmed',
            last_name='Samy',
        )
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor,
            specialization='Cardiology',
            license_number='TEST-LIC-001',
            consultation_duration_minutes=30,
        )

        self.patient = User.objects.create_user(
            username='patient1',
            email='patient@clinic.com',
            password='clinic1234',
            first_name='Khaled',
            last_name='Mostafa',
        )
        self.patient_profile = PatientProfile.objects.create(user=self.patient)

        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@clinic.com',
            password='clinic1234',
            first_name='Admin',
            last_name='User',
        )

        self._create_appointment(1, 9, Appointment.Status.CONFIRMED)
        self._create_appointment(2, 10, Appointment.Status.COMPLETED)
        self._create_appointment(3, 11, Appointment.Status.NO_SHOW)
        self._create_appointment(4, 12, Appointment.Status.REQUESTED)

    def _create_appointment(self, code_number, hour, status):
        start_dt = timezone.now().replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        end_dt = start_dt + timedelta(minutes=30)

        slot = AppointmentSlot.objects.create(
            doctor=self.doctor_profile,
            slot_date=start_dt.date(),
            start_datetime=start_dt,
            end_datetime=end_dt,
            status=AppointmentSlot.Status.BOOKED,
        )

        return Appointment.objects.create(
            appointment_code=f'APT-TEST-{code_number:03d}',
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            slot=slot,
            scheduled_start=start_dt,
            scheduled_end=end_dt,
            status=status,
        )

    def test_get_today_appointments_count(self):
        result = selectors.get_today_appointments_count()
        self.assertEqual(result, 4)

    def test_get_appointments_by_status(self):
        result = selectors.get_appointments_by_status()
        self.assertIn('CONFIRMED', result)
        self.assertIn('COMPLETED', result)
        self.assertEqual(result['NO_SHOW'], 1)

    def test_get_pending_appointments_count(self):
        result = selectors.get_pending_appointments_count()
        self.assertEqual(result, 1)

    def test_get_noshow_rate(self):
        result = selectors.get_noshow_rate(days_back=30)
        self.assertIn('total',   result)
        self.assertIn('noshows', result)
        self.assertIn('rate',    result)
        self.assertEqual(result['noshows'], 1)

    def test_get_noshow_rate_zero_total(self):
        Appointment.objects.all().delete()
        result = selectors.get_noshow_rate(days_back=30)
        self.assertEqual(result['rate'], 0.0)

    def test_get_total_patients_count(self):
        result = selectors.get_total_patients_count()
        self.assertEqual(result, 1)

    def test_get_recent_audit_logs(self):
        AuditLog.log(user=self.admin, action='LOGIN', target_model='User')
        AuditLog.log(user=self.admin, action='EXPORT', target_model='Appointment')
        result = selectors.get_recent_audit_logs(limit=10)
        self.assertEqual(result.count(), 2)

    def test_get_doctor_today_queue(self):
        result = selectors.get_doctor_today_queue(self.doctor.id)
        self.assertEqual(result.count(), 4)