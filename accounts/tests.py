from django.test import TestCase
from django.urls import reverse

from accounts.factories import DoctorProfileFactory, PatientProfileFactory
from accounts.forms import DoctorProfileForm
from accounts.models import User


class AuthRoutingTests(TestCase):
	def setUp(self):
		self.patient = User(
			username="patient1",
			email="patient1@example.com",
		)
		self.patient.set_password("Password123!")
		self.patient._target_role = "patient"
		self.patient.save()

		self.doctor = User(
			username="doctor1",
			email="doctor1@example.com",
		)
		self.doctor.set_password("Password123!")
		self.doctor._target_role = "doctor"
		self.doctor.save()

	def test_patient_login_redirects_to_patient_dashboard(self):
		response = self.client.post(
			reverse("accounts:patient_login"),
			{"username": "patient1", "password": "Password123!"},
		)
		self.assertRedirects(response, reverse("accounts:patient_dashboard"))

	def test_staff_login_redirects_to_doctor_dashboard(self):
		response = self.client.post(
			reverse("accounts:staff_login"),
			{"username": "doctor1", "password": "Password123!"},
		)
		self.assertRedirects(response, reverse("accounts:doctor_dashboard"))

	def test_patient_cannot_use_staff_login(self):
		response = self.client.post(
			reverse("accounts:staff_login"),
			{"username": "patient1", "password": "Password123!"},
		)
		self.assertRedirects(response, reverse("accounts:patient_login"))

	def test_staff_cannot_use_patient_login(self):
		response = self.client.post(
			reverse("accounts:patient_login"),
			{"username": "doctor1", "password": "Password123!"},
		)
		self.assertRedirects(response, reverse("accounts:staff_login"))

	def test_signed_in_user_cannot_access_login_pages(self):
		self.client.force_login(self.patient)

		response = self.client.get(reverse("accounts:patient_login"))
		self.assertRedirects(response, reverse("accounts:patient_dashboard"))

		response = self.client.get(reverse("accounts:staff_login"))
		self.assertRedirects(response, reverse("accounts:patient_dashboard"))

	def test_patient_dashboard_sidebar_matches_patient_permissions(self):
		patient = PatientProfileFactory(user=self.patient)
		self.client.force_login(patient.user)

		response = self.client.get(reverse("accounts:patient_dashboard"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "New Appointment")
		self.assertContains(response, "My EMR")
		self.assertNotContains(response, "Doctor Queue")

	def test_doctor_dashboard_sidebar_matches_doctor_permissions(self):
		doctor = DoctorProfileFactory(user=self.doctor)
		self.client.force_login(doctor.user)

		response = self.client.get(reverse("accounts:doctor_dashboard"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Doctor Queue")
		self.assertContains(response, "Weekly View")
		self.assertContains(response, "Appointments")
		self.assertNotContains(response, "New Appointment")


class DoctorProfileFormTests(TestCase):
	def test_saves_license_number_and_consultation_fee(self):
		doctor = DoctorProfileFactory()

		form = DoctorProfileForm(
			data={
				"username": doctor.user.username,
				"email": doctor.user.email,
				"first_name": doctor.user.first_name,
				"last_name": doctor.user.last_name,
				"phone": doctor.user.phone,
				"specialization": "Cardiology",
				"license_number": "LIC-UPDATED-001",
				"consultation_fee": "275.50",
				"consultation_duration_minutes": "30",
				"buffer_before_minutes": "10",
				"buffer_after_minutes": "5",
				"bio": "Updated profile.",
			},
			instance=doctor.user,
		)

		self.assertTrue(form.is_valid(), form.errors)
		form.save()
		doctor.refresh_from_db()

		self.assertEqual(doctor.license_number, "LIC-UPDATED-001")
		self.assertEqual(str(doctor.consultation_fee), "275.50")

	def test_rejects_duplicate_license_number(self):
		existing = DoctorProfileFactory(license_number="LIC-DUPLICATE")
		doctor = DoctorProfileFactory()

		form = DoctorProfileForm(
			data={
				"username": doctor.user.username,
				"email": doctor.user.email,
				"first_name": doctor.user.first_name,
				"last_name": doctor.user.last_name,
				"phone": doctor.user.phone,
				"specialization": doctor.specialization,
				"license_number": existing.license_number,
				"consultation_fee": "150.00",
				"consultation_duration_minutes": "15",
				"buffer_before_minutes": "5",
				"buffer_after_minutes": "5",
				"bio": doctor.bio,
			},
			instance=doctor.user,
		)

		self.assertFalse(form.is_valid())
		self.assertIn("license_number", form.errors)
