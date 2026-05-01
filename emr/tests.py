# Create your tests here.
from django.test import TestCase
from django.urls import reverse

from accounts.factories import DoctorProfileFactory, PatientProfileFactory
from appointments.factories import AppointmentFactory
from appointments.models import Appointment
from notifications.models import Notification
from .factories import ConsultationRecordFactory


class EMRViewsTests(TestCase):
	def test_doctor_can_open_and_create_consultation_for_checked_in_appointment(self):
		doctor = DoctorProfileFactory()
		patient = PatientProfileFactory()
		appointment = AppointmentFactory(
			doctor=doctor,
			patient=patient,
			status=Appointment.Status.CHECKED_IN,
		)

		self.client.force_login(doctor.user)

		response = self.client.get(reverse('emr:create', args=[appointment.id]))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Finalize Consultation')

		post_response = self.client.post(reverse('emr:create', args=[appointment.id]), {
			'diagnosis': 'Acute viral upper respiratory infection',
			'notes': 'Patient has cough and fever with no red flags.',
			'summary_for_patient': 'Rest, hydration, and follow-up if symptoms worsen.',
			'prescriptions-TOTAL_FORMS': '0',
			'prescriptions-INITIAL_FORMS': '0',
			'prescriptions-MIN_NUM_FORMS': '0',
			'prescriptions-MAX_NUM_FORMS': '1000',
			'tests-TOTAL_FORMS': '0',
			'tests-INITIAL_FORMS': '0',
			'tests-MIN_NUM_FORMS': '0',
			'tests-MAX_NUM_FORMS': '1000',
		})

		self.assertEqual(post_response.status_code, 302)
		appointment.refresh_from_db()
		self.assertEqual(appointment.status, Appointment.Status.COMPLETED)
		self.assertTrue(hasattr(appointment, 'consultation_record'))
		self.assertTrue(
			Notification.objects.filter(
				recipient=appointment.patient.user,
				verb='Consultation completed',
				target_object_id=str(appointment.id),
			).exists()
		)

	def test_patient_can_view_own_consultation_list_and_detail(self):
		consultation = ConsultationRecordFactory()
		patient_user = consultation.appointment.patient.user

		self.client.force_login(patient_user)

		list_response = self.client.get(reverse('emr:patient_list'))
		self.assertEqual(list_response.status_code, 200)
		self.assertContains(list_response, consultation.appointment.appointment_code)

		detail_response = self.client.get(reverse('emr:detail', args=[consultation.id]))
		self.assertEqual(detail_response.status_code, 200)
		self.assertContains(detail_response, consultation.diagnosis)

	def test_patient_cannot_view_other_patient_consultation(self):
		consultation = ConsultationRecordFactory()
		other_patient = PatientProfileFactory()

		self.client.force_login(other_patient.user)

		response = self.client.get(reverse('emr:detail', args=[consultation.id]))
		self.assertEqual(response.status_code, 403)
from django.test import TestCase