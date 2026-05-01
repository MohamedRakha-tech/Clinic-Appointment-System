# Create your tests here.
from django.test import TestCase
from django.urls import reverse

from accounts.factories import DoctorProfileFactory, ReceptionistProfileFactory
from appointments.factories import AppointmentFactory
from appointments.models import Appointment
from notifications.models import Notification
from .factories import AppointmentCheckinFactory


class QueueingViewsTests(TestCase):
	def test_reception_monitor_exposes_pending_checkin_action(self):
		receptionist = ReceptionistProfileFactory()
		appointment = AppointmentFactory(status=Appointment.Status.CONFIRMED)

		self.client.force_login(receptionist.user)

		response = self.client.get(reverse('queueing:reception_queue'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Pending Check-Ins')
		self.assertContains(response, reverse('queueing:checkin', args=[appointment.id]))

	def test_receptionist_can_check_in_confirmed_appointment(self):
		receptionist = ReceptionistProfileFactory()
		appointment = AppointmentFactory(status=Appointment.Status.CONFIRMED)

		self.client.force_login(receptionist.user)

		response = self.client.post(reverse('queueing:checkin', args=[appointment.id]), {
			'confirmation': 'on',
		})

		self.assertEqual(response.status_code, 302)
		appointment.refresh_from_db()
		self.assertEqual(appointment.status, Appointment.Status.CHECKED_IN)
		self.assertTrue(appointment.checkin)
		self.assertTrue(
			Notification.objects.filter(
				recipient=appointment.patient.user,
				verb='Check-in completed',
				target_object_id=str(appointment.id),
			).exists()
		)
		self.assertTrue(
			Notification.objects.filter(
				recipient=appointment.doctor.user,
				verb='Patient checked in',
				target_object_id=str(appointment.id),
			).exists()
		)

	def test_check_in_rejects_non_confirmed_appointments(self):
		receptionist = ReceptionistProfileFactory()
		appointment = AppointmentFactory(status=Appointment.Status.REQUESTED)

		self.client.force_login(receptionist.user)

		response = self.client.post(reverse('queueing:checkin', args=[appointment.id]), {
			'confirmation': 'on',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Only CONFIRMED appointments can be checked in.')
		appointment.refresh_from_db()
		self.assertEqual(appointment.status, Appointment.Status.REQUESTED)

	def test_doctor_queue_shows_checked_in_patient(self):
		doctor = DoctorProfileFactory()
		appointment = AppointmentFactory(doctor=doctor, status=Appointment.Status.CHECKED_IN)
		AppointmentCheckinFactory(appointment=appointment)

		self.client.force_login(doctor.user)

		response = self.client.get(reverse('queueing:doctor_queue'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, appointment.appointment_code)
from django.test import TestCase