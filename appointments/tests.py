from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import DoctorProfileFactory, PatientProfileFactory, ReceptionistProfileFactory
from appointments.factories import AppointmentFactory
from appointments.models import Appointment
from emr.models import ConsultationRecord
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

    def test_doctor_list_shows_only_their_appointments(self):
        doctor_one = DoctorProfileFactory()
        doctor_two = DoctorProfileFactory()
        own_appointment = AppointmentFactory(doctor=doctor_one)
        other_appointment = AppointmentFactory(doctor=doctor_two)

        self.client.force_login(doctor_one.user)
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

    def test_booking_rejects_overlapping_patient_appointment(self):
        patient = PatientProfileFactory()
        doctor_one = DoctorProfileFactory()
        doctor_two = DoctorProfileFactory()
        first_slot = AppointmentSlotFactory(
            doctor=doctor_one,
            slot_date=timezone.localdate() + timedelta(days=2),
            start_datetime=timezone.now() + timedelta(days=2, hours=1),
            end_datetime=timezone.now() + timedelta(days=2, hours=1, minutes=30),
        )
        overlapping_slot = AppointmentSlotFactory(
            doctor=doctor_two,
            slot_date=timezone.localdate() + timedelta(days=2),
            start_datetime=timezone.now() + timedelta(days=2, hours=1, minutes=15),
            end_datetime=timezone.now() + timedelta(days=2, hours=1, minutes=45),
        )
        AppointmentFactory(patient=patient, doctor=doctor_one, slot=first_slot)

        self.client.force_login(patient.user)
        response = self.client.post(reverse("appointment-book"), {
            "doctor_id": doctor_two.id,
            "slot_id": overlapping_slot.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "overlaps with this time")

    def test_booking_rejects_doctor_buffer_conflict(self):
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory(buffer_before_minutes=15, buffer_after_minutes=15)
        first_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=3),
            start_datetime=timezone.now() + timedelta(days=3, hours=1),
            end_datetime=timezone.now() + timedelta(days=3, hours=1, minutes=30),
        )
        buffered_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=3),
            start_datetime=first_slot.end_datetime + timedelta(minutes=10),
            end_datetime=first_slot.end_datetime + timedelta(minutes=40),
        )
        AppointmentFactory(patient=PatientProfileFactory(), doctor=doctor, slot=first_slot)

        self.client.force_login(patient.user)
        response = self.client.post(reverse("appointment-book"), {
            "doctor_id": doctor.id,
            "slot_id": buffered_slot.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "buffer window")

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
        self.assertEqual(appointment.display_status, "Rescheduled")
        self.assertEqual(appointment.slot_id, new_slot.id)
        self.assertEqual(old_slot.status, "AVAILABLE")
        self.assertEqual(new_slot.status, "BOOKED")
        self.assertEqual(appointment.reschedule_history.count(), 1)

    def test_reschedule_page_defaults_to_appointment_date_and_loads_slots_api(self):
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()
        old_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=10),
            start_datetime=timezone.now() + timedelta(days=10, hours=1),
            end_datetime=timezone.now() + timedelta(days=10, hours=1, minutes=30),
        )
        AppointmentSlotFactory(
            doctor=doctor,
            slot_date=old_slot.slot_date,
            start_datetime=timezone.now() + timedelta(days=10, hours=2),
            end_datetime=timezone.now() + timedelta(days=10, hours=2, minutes=30),
        )
        appointment = AppointmentFactory(patient=patient, doctor=doctor, slot=old_slot, status=Appointment.Status.CONFIRMED)

        self.client.force_login(patient.user)
        response = self.client.get(reverse("appointment-reschedule", args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{old_slot.slot_date.isoformat()}"')
        self.assertContains(response, "Load Slots")
        self.assertContains(response, reverse("scheduling_api:slot-available"))

    def test_completion_requires_consultation_record(self):
        receptionist = ReceptionistProfileFactory()
        appointment = AppointmentFactory(status=Appointment.Status.CHECKED_IN)

        self.client.force_login(receptionist.user)
        response = self.client.post(reverse("appointments_api:appointment-complete", args=[appointment.pk]))

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "consultation record must exist", status_code=400)

    def test_completion_succeeds_after_consultation_record_exists(self):
        doctor = DoctorProfileFactory()
        appointment = AppointmentFactory(doctor=doctor, status=Appointment.Status.CHECKED_IN)
        ConsultationRecord.objects.create(
            appointment=appointment,
            doctor=doctor,
            diagnosis="Hypertension follow-up",
            notes="Vitals reviewed, stable exam.",
            requested_tests="",
            summary_for_patient="Continue current medication and return in 4 weeks.",
        )

        receptionist = ReceptionistProfileFactory()
        self.client.force_login(receptionist.user)
        response = self.client.post(reverse("appointments_api:appointment-complete", args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

    def test_appointment_api_books_for_patient(self):
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()
        slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=6),
            start_datetime=timezone.now() + timedelta(days=6, hours=1),
            end_datetime=timezone.now() + timedelta(days=6, hours=1, minutes=30),
        )

        api_client = APIClient()
        api_client.force_authenticate(user=patient.user)
        response = api_client.post(
            reverse("appointments_api:appointment-list"),
            {"slot_id": slot.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Appointment.objects.filter(slot=slot, patient=patient).exists())

    def test_appointment_api_reschedules_and_records_audit_trail(self):
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()
        old_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=6),
            start_datetime=timezone.now() + timedelta(days=6, hours=1),
            end_datetime=timezone.now() + timedelta(days=6, hours=1, minutes=30),
        )
        new_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=7),
            start_datetime=timezone.now() + timedelta(days=7, hours=2),
            end_datetime=timezone.now() + timedelta(days=7, hours=2, minutes=30),
        )
        appointment = AppointmentFactory(patient=patient, doctor=doctor, slot=old_slot, status=Appointment.Status.CONFIRMED)

        api_client = APIClient()
        api_client.force_authenticate(user=patient.user)
        response = api_client.post(
            reverse("appointments_api:appointment-reschedule", args=[appointment.pk]),
            {"slot_id": new_slot.id, "reason": "Need a later time"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Appointment.Status.REQUESTED)
        self.assertEqual(response.data["status_display"], "Rescheduled")
        self.assertTrue(response.data["was_rescheduled"])
        appointment.refresh_from_db()
        self.assertEqual(appointment.slot_id, new_slot.id)

        history = appointment.reschedule_history.get()
        self.assertEqual(history.old_start_datetime, old_slot.start_datetime)
        self.assertEqual(history.new_start_datetime, new_slot.start_datetime)
        self.assertEqual(history.changed_by, patient.user)
        self.assertEqual(history.reason, "Need a later time")

    def test_appointment_api_history_returns_reschedule_audit_trail(self):
        receptionist = ReceptionistProfileFactory()
        patient = PatientProfileFactory()
        doctor = DoctorProfileFactory()
        old_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=8),
            start_datetime=timezone.now() + timedelta(days=8, hours=1),
            end_datetime=timezone.now() + timedelta(days=8, hours=1, minutes=30),
        )
        new_slot = AppointmentSlotFactory(
            doctor=doctor,
            slot_date=timezone.localdate() + timedelta(days=9),
            start_datetime=timezone.now() + timedelta(days=9, hours=2),
            end_datetime=timezone.now() + timedelta(days=9, hours=2, minutes=30),
        )
        appointment = AppointmentFactory(patient=patient, doctor=doctor, slot=old_slot, status=Appointment.Status.CONFIRMED)

        api_client = APIClient()
        api_client.force_authenticate(user=receptionist.user)
        api_client.post(
            reverse("appointments_api:appointment-reschedule", args=[appointment.pk]),
            {"slot_id": new_slot.id, "reason": "Doctor schedule changed"},
            format="json",
        )

        response = api_client.get(reverse("appointments_api:appointment-history", args=[appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["appointment"], appointment.id)
        self.assertEqual(response.data["appointment_code"], appointment.appointment_code)
        self.assertEqual(len(response.data["reschedule_history"]), 1)
        reschedule_entry = response.data["reschedule_history"][0]
        self.assertEqual(reschedule_entry["old_start_datetime"], old_slot.start_datetime.isoformat().replace("+00:00", "Z"))
        self.assertEqual(reschedule_entry["new_start_datetime"], new_slot.start_datetime.isoformat().replace("+00:00", "Z"))
        self.assertEqual(reschedule_entry["changed_by"], receptionist.user.id)
        changed_by_name = f"{receptionist.user.first_name} {receptionist.user.last_name}".strip()
        self.assertEqual(reschedule_entry["changed_by_name"], changed_by_name or receptionist.user.username)
        self.assertEqual(reschedule_entry["reason"], "Doctor schedule changed")
        self.assertIn("created_at", reschedule_entry)

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
