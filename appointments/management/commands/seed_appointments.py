import random
from calendar import monthrange
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import DoctorProfile, PatientProfile
from accounts.services import get_patient_profile_defaults
from appointments.models import Appointment
from scheduling.models import AppointmentSlot


class Command(BaseCommand):
    help = "Seed historical appointment slots and appointments for dashboard testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=36,
            help="How many months of history to seed.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic output.",
        )
        parser.add_argument(
            "--bootstrap",
            action="store_true",
            help="Create demo doctors and patients if none exist.",
        )

    def handle(self, *args, **options):
        months = max(1, options["months"])
        random.seed(options["seed"])

        with transaction.atomic():
            doctors, patients = self._get_participants(bootstrap=options["bootstrap"])
            if not doctors or not patients:
                self.stdout.write(self.style.ERROR("Need at least one doctor and one patient to seed appointments."))
                return

            slot_count, appointment_count = self._seed_historical_appointments(
                doctors=doctors,
                patients=patients,
                months=months,
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {slot_count} slots and {appointment_count} appointments."))
        self.stdout.write(self.style.SUCCESS("Use /accounts/patient/login/ or /accounts/staff/login/ to test the dashboards."))

    def _get_participants(self, bootstrap=False):
        doctors = list(DoctorProfile.objects.select_related("user").order_by("id"))
        patients = list(PatientProfile.objects.select_related("user").order_by("id"))

        if doctors and patients:
            return doctors, patients

        if not bootstrap:
            return doctors, patients

        User = get_user_model()

        if not doctors:
            demo_doctors = [
                ("apptdoc1", "apptdoc1@clinic.com", "Amina", "Saleh", "Cardiology", "LIC-APPT-001"),
                ("apptdoc2", "apptdoc2@clinic.com", "Omar", "Hassan", "Neurology", "LIC-APPT-002"),
                ("apptdoc3", "apptdoc3@clinic.com", "Sara", "Fahmy", "Pediatrics", "LIC-APPT-003"),
            ]
            for username, email, first_name, last_name, specialization, license_number in demo_doctors:
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_staff": False,
                    },
                )
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.is_active = True
                user.set_password("clinic1234")
                user.save()
                profile, _ = DoctorProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "specialization": specialization,
                        "license_number": license_number,
                        "consultation_duration_minutes": 30,
                        "buffer_before_minutes": 5,
                        "buffer_after_minutes": 5,
                    },
                )
                profile.specialization = specialization
                profile.license_number = license_number
                profile.consultation_duration_minutes = 30
                profile.buffer_before_minutes = 5
                profile.buffer_after_minutes = 5
                profile.save()

            doctors = list(DoctorProfile.objects.select_related("user").order_by("id"))

        if not patients:
            demo_patients = [
                ("apptpatient1", "apptpatient1@clinic.com", "Mona", "Tarek"),
                ("apptpatient2", "apptpatient2@clinic.com", "Khaled", "Mostafa"),
                ("apptpatient3", "apptpatient3@clinic.com", "Rania", "Samir"),
                ("apptpatient4", "apptpatient4@clinic.com", "Youssef", "Adel"),
                ("apptpatient5", "apptpatient5@clinic.com", "Nour", "Ibrahim"),
            ]
            for username, email, first_name, last_name in demo_patients:
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_staff": False,
                    },
                )
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.is_active = True
                user.set_password("clinic1234")
                user.save()
                PatientProfile.objects.get_or_create(
                    user=user,
                    defaults=get_patient_profile_defaults(),
                )

            patients = list(PatientProfile.objects.select_related("user").order_by("id"))

        return doctors, patients

    def _seed_historical_appointments(self, doctors, patients, months):
        today = timezone.localdate()
        slot_count = 0
        appointment_count = 0

        status_plan = [
            Appointment.Status.COMPLETED,
            Appointment.Status.CONFIRMED,
            Appointment.Status.REQUESTED,
            Appointment.Status.NO_SHOW,
            Appointment.Status.CANCELLED,
            Appointment.Status.CHECKED_IN,
        ]
        day_choices = (5, 12, 19, 26)
        time_choices = (time(9, 0), time(10, 30), time(12, 0), time(14, 0))

        for month_offset in range(months - 1, -1, -1):
            month_start = self._shift_month(today, -month_offset)
            last_day = monthrange(month_start.year, month_start.month)[1]

            for day_index, day_choice in enumerate(day_choices):
                slot_date = month_start.replace(day=min(day_choice, last_day))
                for doctor_index, doctor in enumerate(doctors):
                    start_time = time_choices[(day_index + doctor_index) % len(time_choices)]
                    slot_start = timezone.make_aware(datetime.combine(slot_date, start_time))
                    slot_end = slot_start + timedelta(minutes=30)

                    slot, _ = AppointmentSlot.objects.get_or_create(
                        doctor=doctor,
                        start_datetime=slot_start,
                        end_datetime=slot_end,
                        defaults={
                            "slot_date": slot_date,
                            "status": AppointmentSlot.Status.BOOKED,
                            "generated_from": AppointmentSlot.GeneratedFrom.MANUAL,
                        },
                    )
                    slot.slot_date = slot_date
                    slot.status = AppointmentSlot.Status.BOOKED
                    slot.generated_from = AppointmentSlot.GeneratedFrom.MANUAL
                    slot.save(update_fields=["slot_date", "status", "generated_from", "updated_at"])
                    slot_count += 1

                    patient = patients[(month_offset + day_index + doctor_index) % len(patients)]
                    status = status_plan[(month_offset + day_index + doctor_index) % len(status_plan)]
                    appointment_code = f"A{slot_date:%y%m%d}{slot_start:%H%M}{doctor.id:02d}"

                    defaults = {
                        "patient": patient,
                        "doctor": doctor,
                        "slot": slot,
                        "scheduled_start": slot_start,
                        "scheduled_end": slot_end,
                        "status": status,
                        "booking_source": Appointment.BookingSource.RECEPTIONIST,
                        "notes_for_staff": f"Seeded appointment for {slot_date:%b %Y}.",
                    }

                    appointment, created = Appointment.objects.update_or_create(
                        slot=slot,
                        defaults={**defaults, "appointment_code": appointment_code},
                    )

                    appointment.patient = patient
                    appointment.doctor = doctor
                    appointment.slot = slot
                    appointment.scheduled_start = slot_start
                    appointment.scheduled_end = slot_end
                    appointment.status = status
                    appointment.booking_source = Appointment.BookingSource.RECEPTIONIST
                    appointment.notes_for_staff = f"Seeded appointment for {slot_date:%b %Y}."
                    appointment.save()
                    appointment_count += 1

        return slot_count, appointment_count

    def _shift_month(self, base_date, months_delta):
        month_index = base_date.year * 12 + (base_date.month - 1) + months_delta
        year, month_offset = divmod(month_index, 12)
        return base_date.replace(year=year, month=month_offset + 1, day=1)
