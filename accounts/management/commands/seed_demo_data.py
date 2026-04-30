from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from accounts.models import AdminProfile, DoctorProfile, PatientProfile, ReceptionistProfile
from appointments.factories import AppointmentFactory
from scheduling.factories import DoctorWeeklyScheduleFactory
from scheduling.models import AppointmentSlot
from scheduling.services import SlotGenerationService
from accounts.services import ensure_profile_for_role

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo users, schedules, slots, and a sample appointment for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Password123!",
            help="Password to set for the demo users.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="How many days of slots to generate starting from today.",
        )
        parser.add_argument(
            "--with-appointment",
            action="store_true",
            help="Create one sample appointment so detail/status pages have data.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        days = options["days"]

        patient_primary = self._seed_user(
            username="patient_demo",
            email="patient_demo@example.com",
            password=password,
            role="patient",
            first_name="Pat",
            last_name="Primary",
        )
        patient_other = self._seed_user(
            username="patient_other",
            email="patient_other@example.com",
            password=password,
            role="patient",
            first_name="Pat",
            last_name="Other",
        )
        doctor = self._seed_user(
            username="doctor_demo",
            email="doctor_demo@example.com",
            password=password,
            role="doctor",
            first_name="Dana",
            last_name="Doctor",
        )
        receptionist = self._seed_user(
            username="reception_demo",
            email="reception_demo@example.com",
            password=password,
            role="receptionist",
            is_staff=True,
            first_name="Ria",
            last_name="Reception",
        )
        admin = self._seed_user(
            username="admin_demo",
            email="admin_demo@example.com",
            password=password,
            role="admin",
            is_staff=True,
            first_name="Ava",
            last_name="Admin",
            is_superuser=False,
        )

        # Get profile objects for factories and services
        doctor_profile = DoctorProfile.objects.get(user=doctor)
        patient_primary_profile = PatientProfile.objects.get(user=patient_primary)

        DoctorWeeklyScheduleFactory(doctor=doctor_profile, day_of_week=timezone.localdate().weekday())
        DoctorWeeklyScheduleFactory(doctor=doctor_profile, day_of_week=(timezone.localdate().weekday() + 1) % 7)

        start_date = timezone.localdate()
        end_date = start_date + timedelta(days=days)
        summary = SlotGenerationService().generate_slots_for_doctor(doctor_profile, start_date, end_date)

        self.stdout.write(self.style.SUCCESS("Seeded demo users, schedules, and slots."))
        self.stdout.write(f"Patient 1: {patient_primary.username} / {password}")
        self.stdout.write(f"Patient 2: {patient_other.username} / {password}")
        self.stdout.write(f"Doctor: {doctor.username} / {password}")
        self.stdout.write(f"Receptionist: {receptionist.username} / {password}")
        self.stdout.write(f"Admin: {admin.username} / {password}")
        self.stdout.write(f"Created slots: {summary['created_count']}")

        if options["with_appointment"]:
            slot = (
                AppointmentSlot.objects.filter(doctor=doctor_profile, status=AppointmentSlot.Status.AVAILABLE)
                .order_by("start_datetime")
                .first()
            )
            if slot is None:
                self.stdout.write(self.style.WARNING("No available slot found for sample appointment."))
                return

            appointment = AppointmentFactory(patient=patient_primary_profile, doctor=doctor_profile, slot=slot)
            self.stdout.write(f"Sample appointment created: {appointment.appointment_code}")

    def _seed_user(
        self,
        *,
        username,
        email,
        password,
        role,
        first_name="",
        last_name="",
        is_staff=False,
        is_superuser=False,
    ):
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = is_staff or role == "admin"
        user.is_superuser = is_superuser
        user.is_active = True
        user.set_password(password)
        user._target_role = role
        user.save()

        if role == "patient":
            PatientProfile.objects.update_or_create(user=user, defaults={})
        elif role == "doctor":
            DoctorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "specialization": "General Medicine",
                    "license_number": f"DOC-{user.id}",
                    "consultation_duration_minutes": 15,
                    "buffer_before_minutes": 5,
                    "buffer_after_minutes": 5,
                    "bio": "Demo doctor profile for appointment testing.",
                },
            )
        elif role == "receptionist":
            ReceptionistProfile.objects.update_or_create(
                user=user,
                defaults={"employee_code": f"REC-{user.id}"},
            )
        elif role == "admin":
            AdminProfile.objects.update_or_create(
                user=user,
                defaults={"employee_code": f"ADM-{user.id}"},
            )

        ensure_profile_for_role(user, role)
        return user
