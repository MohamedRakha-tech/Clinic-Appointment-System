from datetime import date, time, timedelta
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AdminProfile, DoctorProfile, ReceptionistProfile, User
from accounts.utils import set_user_role
from scheduling.models import (
    AppointmentSlot,
    DoctorScheduleException,
    DoctorWeeklySchedule,
)
from scheduling.selectors import get_available_slots, is_slot_available
from scheduling.services import SlotGenerationService


class SchedulingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="doctor1",
            email="doctor1@example.com",
            password="password",
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.user,
            specialization="Cardiology",
            license_number="DOC-001",
            consultation_duration_minutes=15,
            buffer_before_minutes=5,
            buffer_after_minutes=5,
        )

    def make_datetime(self, target_date, target_time):
        return timezone.make_aware(
            timezone.datetime.combine(target_date, target_time),
            timezone.get_current_timezone(),
        )


class DoctorWeeklyScheduleValidationTests(SchedulingTestCase):
    def test_weekly_schedule_start_time_must_be_before_end_time(self):
        schedule = DoctorWeeklySchedule(
            doctor=self.doctor,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(9, 0),
        )

        with self.assertRaises(ValidationError):
            schedule.full_clean()

    def test_day_of_week_must_be_between_zero_and_six(self):
        schedule = DoctorWeeklySchedule(
            doctor=self.doctor,
            day_of_week=7,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        with self.assertRaises(ValidationError):
            schedule.full_clean()


class SlotGenerationServiceTests(SchedulingTestCase):
    def test_normal_weekly_slot_generation_works(self):
        target_date = date(2026, 4, 27)
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        summary = SlotGenerationService().generate_slots_for_doctor(
            self.doctor,
            target_date,
            target_date,
        )

        self.assertEqual(summary["created_count"], 2)
        self.assertEqual(AppointmentSlot.objects.count(), 2)

    def test_slot_duration_uses_doctor_consultation_duration_minutes(self):
        self.doctor.consultation_duration_minutes = 20
        self.doctor.buffer_before_minutes = 0
        self.doctor.buffer_after_minutes = 0
        self.doctor.save()
        target_date = date(2026, 4, 27)
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        SlotGenerationService().generate_slots_for_doctor(
            self.doctor,
            target_date,
            target_date,
        )

        slot = AppointmentSlot.objects.order_by("start_datetime").first()
        self.assertEqual(slot.end_datetime - slot.start_datetime, timedelta(minutes=20))

    def test_buffer_time_uses_doctor_buffer_before_and_after_minutes(self):
        self.doctor.consultation_duration_minutes = 15
        self.doctor.buffer_before_minutes = 5
        self.doctor.buffer_after_minutes = 10
        self.doctor.save()
        target_date = date(2026, 4, 27)
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        SlotGenerationService().generate_slots_for_doctor(
            self.doctor,
            target_date,
            target_date,
        )

        slots = list(AppointmentSlot.objects.order_by("start_datetime"))
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[1].start_datetime - slots[0].start_datetime, timedelta(minutes=30))

    def test_day_off_exception_prevents_weekly_slot_generation(self):
        target_date = date(2026, 4, 27)
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        DoctorScheduleException.objects.create(
            doctor=self.doctor,
            exception_date=target_date,
            type=DoctorScheduleException.ExceptionType.DAY_OFF,
        )

        SlotGenerationService().generate_slots_for_doctor(
            self.doctor,
            target_date,
            target_date,
        )

        self.assertEqual(AppointmentSlot.objects.count(), 0)

    def test_vacation_exception_prevents_weekly_slot_generation(self):
        target_date = date(2026, 4, 27)
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        DoctorScheduleException.objects.create(
            doctor=self.doctor,
            exception_date=target_date,
            type=DoctorScheduleException.ExceptionType.VACATION,
        )

        SlotGenerationService().generate_slots_for_doctor(
            self.doctor,
            target_date,
            target_date,
        )

        self.assertEqual(AppointmentSlot.objects.count(), 0)

    def test_special_working_day_generates_exception_slots(self):
        target_date = date(2026, 4, 28)
        DoctorScheduleException.objects.create(
            doctor=self.doctor,
            exception_date=target_date,
            type=DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        summary = SlotGenerationService().generate_slots_for_doctor(
            self.doctor,
            target_date,
            target_date,
        )

        self.assertEqual(summary["created_count"], 2)
        self.assertTrue(
            AppointmentSlot.objects.filter(
                generated_from=AppointmentSlot.GeneratedFrom.EXCEPTION
            ).exists()
        )

    def test_duplicate_slots_are_not_created(self):
        target_date = date(2026, 4, 27)
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        service = SlotGenerationService()

        service.generate_slots_for_doctor(self.doctor, target_date, target_date)
        service.generate_slots_for_doctor(self.doctor, target_date, target_date)

        self.assertEqual(AppointmentSlot.objects.count(), 2)
        self.assertEqual(service.get_generation_summary()["skipped_count"], 2)


class SchedulingSelectorTests(SchedulingTestCase):
    def test_get_available_slots_returns_only_available_future_slots(self):
        future_date = timezone.localdate() + timedelta(days=1)
        past_date = timezone.localdate() - timedelta(days=1)
        future_start = self.make_datetime(future_date, time(9, 0))
        past_start = self.make_datetime(past_date, time(9, 0))
        future_slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=future_date,
            start_datetime=future_start,
            end_datetime=future_start + timedelta(minutes=15),
            status=AppointmentSlot.Status.AVAILABLE,
        )
        AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=future_date,
            start_datetime=future_start + timedelta(hours=1),
            end_datetime=future_start + timedelta(hours=1, minutes=15),
            status=AppointmentSlot.Status.BOOKED,
        )
        AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=past_date,
            start_datetime=past_start,
            end_datetime=past_start + timedelta(minutes=15),
            status=AppointmentSlot.Status.AVAILABLE,
        )

        slots = list(get_available_slots())

        self.assertEqual(slots, [future_slot])

    def test_is_slot_available_returns_false_for_booked_slots(self):
        future_date = timezone.localdate() + timedelta(days=1)
        start_datetime = self.make_datetime(future_date, time(9, 0))
        slot = AppointmentSlot.objects.create(
            doctor=self.doctor,
            slot_date=future_date,
            start_datetime=start_datetime,
            end_datetime=start_datetime + timedelta(minutes=15),
            status=AppointmentSlot.Status.BOOKED,
        )

        self.assertFalse(is_slot_available(slot))


class GenerateSlotsCommandTests(SchedulingTestCase):
    def test_management_command_generates_slots_successfully(self):
        target_date = date(2026, 4, 27)
        DoctorWeeklySchedule.objects.create(
            doctor=self.doctor,
            day_of_week=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        output = StringIO()

        call_command(
            "generate_slots",
            doctor_id=self.doctor.pk,
            start_date=target_date.isoformat(),
            end_date=target_date.isoformat(),
            stdout=output,
        )

        self.assertEqual(AppointmentSlot.objects.count(), 2)
        self.assertIn("Slot generation completed.", output.getvalue())


class SchedulingAccessTests(TestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(
            username="doctor_access",
            email="doctor_access@example.com",
            password="password",
            is_staff=True,
        )
        self.doctor_user._target_role = "doctor"
        self.doctor_user.save()
        self.doctor_profile, _ = DoctorProfile.objects.get_or_create(
            user=self.doctor_user,
            defaults={
                "specialization": "Cardiology",
                "license_number": "DOC-ACCESS-001",
            },
        )
        set_user_role(self.doctor_user, "doctor")

        self.reception_user = User.objects.create_user(
            username="reception_access",
            email="reception_access@example.com",
            password="password",
            is_staff=True,
        )
        self.reception_user._target_role = "receptionist"
        self.reception_user.save()
        ReceptionistProfile.objects.get_or_create(
            user=self.reception_user,
            defaults={"employee_code": "REC-ACCESS-001"},
        )
        set_user_role(self.reception_user, "receptionist")

        self.admin_user = User.objects.create_user(
            username="admin_access",
            email="admin_access@example.com",
            password="password",
            is_staff=True,
        )
        self.admin_user._target_role = "admin"
        self.admin_user.save()
        AdminProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={"employee_code": "ADM-ACCESS-001"},
        )
        set_user_role(self.admin_user, "admin")

        self.patient_user = User.objects.create_user(
            username="patient_access",
            email="patient_access@example.com",
            password="password",
        )
        self.patient_user._target_role = "patient"
        self.patient_user.save()
        set_user_role(self.patient_user, "patient")

    def test_doctor_can_access_only_my_schedule(self):
        self.client.login(username="doctor_access", password="password")

        my_schedule_response = self.client.get(reverse("scheduling:doctor_my_schedule"))
        schedules_response = self.client.get(reverse("scheduling:weekly_schedule_list"))
        slots_response = self.client.get(reverse("scheduling:appointment_slot_list"))
        generate_response = self.client.get(reverse("scheduling:generate_slots"))

        self.assertEqual(my_schedule_response.status_code, 200)
        self.assertEqual(schedules_response.status_code, 403)
        self.assertEqual(slots_response.status_code, 403)
        self.assertEqual(generate_response.status_code, 403)

    def test_receptionist_can_access_scheduling_management(self):
        self.client.login(username="reception_access", password="password")

        response = self.client.get(reverse("scheduling:weekly_schedule_list"))

        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_scheduling_management(self):
        self.client.login(username="admin_access", password="password")

        response = self.client.get(reverse("scheduling:weekly_schedule_list"))

        self.assertEqual(response.status_code, 200)

    def test_patient_cannot_access_scheduling_pages(self):
        self.client.login(username="patient_access", password="password")

        schedules_response = self.client.get(reverse("scheduling:weekly_schedule_list"))
        my_schedule_response = self.client.get(reverse("scheduling:doctor_my_schedule"))

        self.assertEqual(schedules_response.status_code, 403)
        self.assertEqual(my_schedule_response.status_code, 403)
