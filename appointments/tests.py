from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.factories import DoctorProfileFactory, PatientProfileFactory, ReceptionistProfileFactory
from appointments.factories import AppointmentFactory
from appointments.models import Appointment
from scheduling.factories import AppointmentSlotFactory


class AppointmentViewsTests(TestCase):
    def test_patient_list_shows_only_their_appointments(self):
        patient = PatientProfileFactory()
        other_patient = PatientProfileFactory()
        own_appointment = AppointmentFactory(patient=patient)
        other_appointment = AppointmentFactory(patient=other_patient)

        self.client.force_login(patient.user)
        response = self.client.get(reverse("appointment-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_appointment.appointment_code)
        self.assertNotContains(response, other_appointment.appointment_code)

    def test_patient_cannot_open_other_patients_appointment_detail(self):
        appointment = AppointmentFactory()
        other_patient = PatientProfileFactory()

        self.client.force_login(other_patient.user)
        response = self.client.get(reverse("appointment-detail", args=[appointment.pk]))

        self.assertEqual(response.status_code, 404)

    def test_patient_can_book_available_slot_atomically(self):
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()
        slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=1),
            start_datetime=timezone.now() + timedelta(days=1, hours=2),
            end_datetime=timezone.now() + timedelta(days=1, hours=2, minutes=30),
        )

        self.client.force_login(patient.user)
        response = self.client.post(reverse("appointment-book"), {
            "doctor_id": doctor.id,
            "slot_id": slot.id,
        })

        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get(slot=slot)
        self.assertEqual(appointment.patient, patient)
        self.assertEqual(appointment.status, Appointment.Status.REQUESTED)
        slot.refresh_from_db()
        self.assertEqual(slot.status, "BOOKED")

    def test_booking_rejects_taken_slot(self):
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()
        slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=2),
            start_datetime=timezone.now() + timedelta(days=2, hours=1),
            end_datetime=timezone.now() + timedelta(days=2, hours=1, minutes=30),
        )
        AppointmentFactory(patient=PatientProfileFactory(), doctor=doctor, slot=slot)

        self.client.force_login(patient.user)
        response = self.client.post(reverse("appointment-book"), {
            "doctor_id": doctor.id,
            "slot_id": slot.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This slot is no longer available.")

    def test_staff_can_confirm_appointment_and_record_history(self):
        receptionist = ReceptionistProfileFactory()
        appointment = AppointmentFactory(status=Appointment.Status.REQUESTED)

        self.client.force_login(receptionist.user)
        response = self.client.post(reverse("appointment-confirm", args=[appointment.pk]))

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
        self.assertTrue(appointment.status_history.filter(new_status=Appointment.Status.CONFIRMED).exists())

    def test_patient_can_reschedule_and_release_old_slot(self):
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()
        old_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=3),
            start_datetime=timezone.now() + timedelta(days=3, hours=1),
            end_datetime=timezone.now() + timedelta(days=3, hours=1, minutes=30),
        )
        new_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=4),
            start_datetime=timezone.now() + timedelta(days=4, hours=2),
            end_datetime=timezone.now() + timedelta(days=4, hours=2, minutes=30),
        )
        appointment = AppointmentFactory(patient=patient, doctor=doctor, slot=old_slot, status=Appointment.Status.CONFIRMED)

        self.client.force_login(patient.user)
        response = self.client.post(reverse("appointment-reschedule", args=[appointment.pk]), {
            "reason": "Personal scheduling conflict",
            "slot_id": new_slot.id,
        })

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        old_slot.refresh_from_db()
        new_slot.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.REQUESTED)
        self.assertEqual(appointment.slot_id, new_slot.id)
        self.assertEqual(old_slot.status, "AVAILABLE")
        self.assertEqual(new_slot.status, "BOOKED")
        self.assertEqual(appointment.reschedule_history.count(), 1)

    def test_staff_history_view_shows_status_and_reschedule_entries(self):
        receptionist = ReceptionistProfileFactory()
        appointment = AppointmentFactory(status=Appointment.Status.REQUESTED)

        self.client.force_login(receptionist.user)
        self.client.post(reverse("appointment-confirm", args=[appointment.pk]))

        new_slot = AppointmentSlotFactory(
            doctor=appointment.doctor,
            slot_date=timezone.localdate() + timedelta(days=5),
            start_datetime=timezone.now() + timedelta(days=5, hours=3),
            end_datetime=timezone.now() + timedelta(days=5, hours=3, minutes=30),
        )
        self.client.force_login(appointment.patient.user)
        self.client.post(reverse("appointment-reschedule", args=[appointment.pk]), {
            "reason": "Need later time",
            "slot_id": new_slot.id,
        })

        self.client.force_login(receptionist.user)
        response = self.client.get(reverse("appointment-history", args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Status Changes")
        self.assertContains(response, "Reschedule History")
