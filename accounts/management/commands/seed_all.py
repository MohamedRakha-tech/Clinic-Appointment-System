import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.factories import AdminProfileFactory, DoctorProfileFactory, PatientProfileFactory, ReceptionistProfileFactory
from accounts.models import AdminProfile, DoctorProfile, PatientProfile, ReceptionistProfile, User
from appointments.factories import (
    AppointmentCancellationFactory,
    AppointmentFactory,
    AppointmentRescheduleHistoryFactory,
    AppointmentStatusHistoryFactory,
)
from appointments.models import Appointment
from emr.factories import ConsultationRecordFactory, PrescriptionItemFactory, RequestedTestFactory
from queueing.factories import AppointmentCheckinFactory
from scheduling.factories import AppointmentSlotFactory, DoctorScheduleExceptionFactory, DoctorWeeklyScheduleFactory


class Command(BaseCommand):
    help = "Seed all project models with realistic demo data"

    DEMO_PASSWORD = "Password123!"
    DEMO_PATIENT_USERNAME = "patient1"
    DEMO_DOCTOR_USERNAME = "doctor1"
    DEMO_RECEPTIONIST_USERNAME = "reception1"
    DEMO_ADMIN_USERNAME = "admin1"

    def add_arguments(self, parser):
        parser.add_argument("--patients", type=int, default=20)
        parser.add_argument("--doctors", type=int, default=6)
        parser.add_argument("--receptionists", type=int, default=3)
        parser.add_argument("--admins", type=int, default=2)
        parser.add_argument("--weekly-schedules", type=int, default=20)
        parser.add_argument("--exceptions", type=int, default=8)
        parser.add_argument("--slots", type=int, default=120)
        parser.add_argument("--appointments", type=int, default=80)
        parser.add_argument("--clear", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_seeded_data()

        if options["patients"] < 1:
            raise CommandError("--patients must be at least 1")
        if options["doctors"] < 1:
            raise CommandError("--doctors must be at least 1")

        patients = [self._ensure_demo_patient()]
        patients.extend(PatientProfileFactory.create_batch(max(options["patients"] - 1, 0)))
        doctors = [self._ensure_demo_doctor()]
        doctors.extend(DoctorProfileFactory.create_batch(max(options["doctors"] - 1, 0)))
        receptionists = [self._ensure_demo_receptionist()]
        receptionists.extend(ReceptionistProfileFactory.create_batch(max(options["receptionists"] - 1, 0)))
        admins = [self._ensure_demo_admin()]
        admins.extend(AdminProfileFactory.create_batch(max(options["admins"] - 1, 0)))

        staff_users = [item.user for item in receptionists + admins]
        actor_users = staff_users if staff_users else [doctors[0].user] if doctors else []

        for _ in range(options["weekly_schedules"]):
            DoctorWeeklyScheduleFactory(doctor=random.choice(doctors))

        for _ in range(options["exceptions"]):
            DoctorScheduleExceptionFactory(
                doctor=random.choice(doctors),
                created_by=random.choice(actor_users) if actor_users else None,
            )

        slots = [
            AppointmentSlotFactory(doctor=random.choice(doctors))
            for _ in range(options["slots"])
        ]

        appointment_statuses = [
            Appointment.Status.REQUESTED,
            Appointment.Status.CONFIRMED,
            Appointment.Status.CHECKED_IN,
            Appointment.Status.COMPLETED,
            Appointment.Status.CANCELLED,
            Appointment.Status.NO_SHOW,
        ]

        appointments = []
        consultations = []
        usable_slot_count = min(options["appointments"], len(slots))
        for i in range(usable_slot_count):
            slot = slots[i]
            status = random.choice(appointment_statuses)
            appointment = AppointmentFactory(
                slot=slot,
                doctor=slot.doctor,
                patient=random.choice(patients),
                status=status,
                booking_source=random.choice(
                    [
                        Appointment.BookingSource.PATIENT,
                        Appointment.BookingSource.RECEPTIONIST,
                        Appointment.BookingSource.ADMIN,
                    ]
                ),
                confirmed_by=random.choice(actor_users) if status in {Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN, Appointment.Status.COMPLETED} and actor_users else None,
                checked_in_by=random.choice(actor_users) if status in {Appointment.Status.CHECKED_IN, Appointment.Status.COMPLETED} and actor_users else None,
                cancelled_by=random.choice(actor_users) if status == Appointment.Status.CANCELLED and actor_users else None,
                cancellation_reason="Patient request" if status == Appointment.Status.CANCELLED else None,
            )
            appointments.append(appointment)

        # Guarantee data that appears in queue and consultations pages.
        # For each doctor, create:
        # 1) one CHECKED_IN appointment today + checkin row
        # 2) one COMPLETED appointment today + consultation with details
        today_base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        for idx, doctor in enumerate(doctors):
            patient_for_doctor = patients[idx % len(patients)]

            checkin_start = today_base + timedelta(minutes=idx * 40)
            checkin_slot = AppointmentSlotFactory(
                doctor=doctor,
                start_datetime=checkin_start,
                end_datetime=checkin_start + timedelta(minutes=30),
            )
            checked_in_appointment = AppointmentFactory(
                slot=checkin_slot,
                doctor=doctor,
                patient=patient_for_doctor,
                status=Appointment.Status.CHECKED_IN,
                checked_in_by=random.choice(actor_users) if actor_users else None,
                confirmed_by=random.choice(actor_users) if actor_users else None,
                booking_source=Appointment.BookingSource.RECEPTIONIST,
            )
            appointments.append(checked_in_appointment)
            AppointmentCheckinFactory(
                appointment=checked_in_appointment,
                checked_in_by=checked_in_appointment.checked_in_by,
            )

            completed_start = today_base + timedelta(hours=4, minutes=idx * 40)
            completed_slot = AppointmentSlotFactory(
                doctor=doctor,
                start_datetime=completed_start,
                end_datetime=completed_start + timedelta(minutes=30),
            )
            completed_appointment = AppointmentFactory(
                slot=completed_slot,
                doctor=doctor,
                patient=patient_for_doctor,
                status=Appointment.Status.COMPLETED,
                checked_in_by=random.choice(actor_users) if actor_users else None,
                confirmed_by=random.choice(actor_users) if actor_users else None,
                booking_source=Appointment.BookingSource.RECEPTIONIST,
            )
            appointments.append(completed_appointment)
            AppointmentCheckinFactory(
                appointment=completed_appointment,
                checked_in_by=completed_appointment.checked_in_by,
            )
            consultation = ConsultationRecordFactory(
                appointment=completed_appointment,
                doctor=doctor,
            )
            consultations.append(consultation)

        for appointment in appointments:
            if appointment.status != Appointment.Status.REQUESTED:
                AppointmentStatusHistoryFactory(
                    appointment=appointment,
                    old_status=Appointment.Status.REQUESTED,
                    new_status=appointment.status,
                    changed_by=random.choice(actor_users) if actor_users else None,
                )

            if appointment.status in {Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN, Appointment.Status.COMPLETED} and random.random() < 0.35:
                AppointmentRescheduleHistoryFactory(
                    appointment=appointment,
                    changed_by=random.choice(actor_users) if actor_users else None,
                )

            if appointment.status == Appointment.Status.CANCELLED:
                AppointmentCancellationFactory(
                    appointment=appointment,
                    cancelled_by=appointment.cancelled_by,
                    reason=appointment.cancellation_reason or "Cancelled by patient",
                )

            if appointment.status in {Appointment.Status.CHECKED_IN, Appointment.Status.COMPLETED} and not hasattr(appointment, "checkin"):
                AppointmentCheckinFactory(
                    appointment=appointment,
                    checked_in_by=appointment.checked_in_by,
                )

            if appointment.status == Appointment.Status.COMPLETED and not hasattr(appointment, "consultation_record"):
                consultation = ConsultationRecordFactory(appointment=appointment, doctor=appointment.doctor)
                consultations.append(consultation)

        for consultation in consultations:
            for _ in range(random.randint(1, 3)):
                PrescriptionItemFactory(consultation_record=consultation)
            for _ in range(random.randint(1, 2)):
                RequestedTestFactory(consultation_record=consultation)

        self.stdout.write(self.style.SUCCESS("Seed completed successfully."))
        self.stdout.write(
            self.style.NOTICE(
                (
                    "Created: "
                    f"patients={len(patients)}, "
                    f"doctors={len(doctors)}, "
                    f"receptionists={len(receptionists)}, "
                    f"admins={len(admins)}, "
                    f"slots={len(slots)}, "
                    f"appointments={len(appointments)}, "
                    f"consultations={len(consultations)}"
                )
            )
        )
        self.stdout.write(
            self.style.NOTICE("Demo logins: patient1 / doctor1 / reception1 / admin1 (password: Password123!)")
        )

    def _ensure_demo_patient(self):
        user, _ = User.objects.get_or_create(
            username=self.DEMO_PATIENT_USERNAME,
            defaults={
                "email": "patient1@example.com",
                "first_name": "Demo",
                "last_name": "Patient",
                "phone": "1000000000",
                "is_active": True,
                "is_staff": False,
            },
        )
        user.email = "patient1@example.com"
        user.first_name = "Demo"
        user.last_name = "Patient"
        user.phone = "1000000000"
        user.is_active = True
        user.is_staff = False
        user.set_password(self.DEMO_PASSWORD)
        user.save()

        profile, _ = PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                "gender": "Male",
                "address": "Demo Patient Address",
                "emergency_contact_name": "Demo Contact",
                "emergency_contact_phone": "1000000099",
            },
        )
        profile.gender = "Male"
        profile.address = "Demo Patient Address"
        profile.emergency_contact_name = "Demo Contact"
        profile.emergency_contact_phone = "1000000099"
        profile.save()
        return profile

    def _clear_seeded_data(self):
        from appointments.models import Appointment, AppointmentCancellation, AppointmentRescheduleHistory, AppointmentStatusHistory
        from emr.models import ConsultationRecord, PrescriptionItem, RequestedTest
        from queueing.models import AppointmentCheckin
        from scheduling.models import AppointmentSlot, DoctorScheduleException, DoctorWeeklySchedule

        PrescriptionItem.objects.all().delete()
        RequestedTest.objects.all().delete()
        ConsultationRecord.objects.all().delete()
        AppointmentCheckin.objects.all().delete()
        AppointmentCancellation.objects.all().delete()
        AppointmentRescheduleHistory.objects.all().delete()
        AppointmentStatusHistory.objects.all().delete()
        Appointment.objects.all().delete()
        AppointmentSlot.objects.all().delete()
        DoctorScheduleException.objects.all().delete()
        DoctorWeeklySchedule.objects.all().delete()
        PatientProfile.objects.all().delete()
        DoctorProfile.objects.all().delete()
        ReceptionistProfile.objects.all().delete()
        AdminProfile.objects.all().delete()
        User.objects.all().delete()

    def _ensure_demo_doctor(self):
        user, _ = User.objects.get_or_create(
            username=self.DEMO_DOCTOR_USERNAME,
            defaults={
                "email": "doctor1@example.com",
                "first_name": "Demo",
                "last_name": "Doctor",
                "phone": "1000000001",
                "is_active": True,
                "is_staff": False,
            },
        )
        user.email = "doctor1@example.com"
        user.first_name = "Demo"
        user.last_name = "Doctor"
        user.phone = "1000000001"
        user.is_active = True
        user.is_staff = False
        user.set_password(self.DEMO_PASSWORD)
        user.save()

        profile, _ = DoctorProfile.objects.get_or_create(
            user=user,
            defaults={
                "specialization": "General Practice",
                "license_number": "LIC-DEMO-0001",
                "consultation_duration_minutes": 15,
                "buffer_before_minutes": 5,
                "buffer_after_minutes": 5,
                "bio": "Demo doctor account.",
            },
        )
        profile.specialization = "General Practice"
        profile.license_number = "LIC-DEMO-0001"
        profile.consultation_duration_minutes = 15
        profile.buffer_before_minutes = 5
        profile.buffer_after_minutes = 5
        profile.bio = "Demo doctor account."
        profile.save()
        return profile

    def _ensure_demo_receptionist(self):
        user, _ = User.objects.get_or_create(
            username=self.DEMO_RECEPTIONIST_USERNAME,
            defaults={
                "email": "reception1@example.com",
                "first_name": "Demo",
                "last_name": "Receptionist",
                "phone": "1000000002",
                "is_active": True,
                "is_staff": True,
            },
        )
        user.email = "reception1@example.com"
        user.first_name = "Demo"
        user.last_name = "Receptionist"
        user.phone = "1000000002"
        user.is_active = True
        user.is_staff = True
        user.set_password(self.DEMO_PASSWORD)
        user.save()

        profile, _ = ReceptionistProfile.objects.get_or_create(
            user=user,
            defaults={"employee_code": "REC-DEMO-0001"},
        )
        profile.employee_code = "REC-DEMO-0001"
        profile.save()
        return profile

    def _ensure_demo_admin(self):
        user, _ = User.objects.get_or_create(
            username=self.DEMO_ADMIN_USERNAME,
            defaults={
                "email": "admin1@example.com",
                "first_name": "Demo",
                "last_name": "Admin",
                "phone": "1000000003",
                "is_active": True,
                "is_staff": True,
            },
        )
        user.email = "admin1@example.com"
        user.first_name = "Demo"
        user.last_name = "Admin"
        user.phone = "1000000003"
        user.is_active = True
        user.is_staff = True
        user.set_password(self.DEMO_PASSWORD)
        user.save()

        profile, _ = AdminProfile.objects.get_or_create(
            user=user,
            defaults={"employee_code": "ADM-DEMO-0001"},
        )
        profile.employee_code = "ADM-DEMO-0001"
        profile.save()
        return profile
