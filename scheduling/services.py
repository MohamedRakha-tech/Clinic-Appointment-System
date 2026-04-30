from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import DoctorProfile
from scheduling.models import (
    AppointmentSlot,
    DoctorScheduleException,
    DoctorWeeklySchedule,
)


class SlotGenerationService:
    def __init__(self):
        self.summary = {
            "created_count": 0,
            "skipped_count": 0,
            "doctors_processed": 0,
            "errors": [],
        }

    def generate_slots_for_doctor(self, doctor, start_date, end_date):
        self.summary["doctors_processed"] += 1

        try:
            with transaction.atomic():
                current_date = start_date
                while current_date <= end_date:
                    self._generate_slots_for_doctor_date(doctor, current_date)
                    current_date += timedelta(days=1)
        except Exception as exc:
            self.summary["errors"].append(
                f"Doctor {doctor.pk}: {exc}"
            )

        return self.get_generation_summary()

    def generate_slots_for_all_doctors(self, start_date, end_date):
        doctors = DoctorProfile.objects.all()

        for doctor in doctors:
            self.generate_slots_for_doctor(doctor, start_date, end_date)

        return self.get_generation_summary()

    @transaction.atomic
    def generate_slots_for_weekly_schedule(self, schedule, target_date):
        if not schedule.is_active or schedule.day_of_week != target_date.weekday():
            self.summary["skipped_count"] += 1
            return []

        return self._create_slots(
            doctor=schedule.doctor,
            slot_date=target_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            generated_from=AppointmentSlot.GeneratedFrom.WEEKLY_SCHEDULE,
        )

    @transaction.atomic
    def generate_slots_for_special_working_day(self, exception):
        if exception.type != DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY:
            self.summary["skipped_count"] += 1
            return []

        return self._create_slots(
            doctor=exception.doctor,
            slot_date=exception.exception_date,
            start_time=exception.start_time,
            end_time=exception.end_time,
            generated_from=AppointmentSlot.GeneratedFrom.EXCEPTION,
        )

    def get_generation_summary(self):
        return {
            "created_count": self.summary["created_count"],
            "skipped_count": self.summary["skipped_count"],
            "doctors_processed": self.summary["doctors_processed"],
            "errors": list(self.summary["errors"]),
        }

    def _generate_slots_for_doctor_date(self, doctor, target_date):
        exceptions = DoctorScheduleException.objects.filter(
            doctor=doctor,
            exception_date=target_date,
        )

        for exception in exceptions.filter(
            type=DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY
        ):
            self.generate_slots_for_special_working_day(exception)

        has_blocking_exception = exceptions.filter(
            type__in=[
                DoctorScheduleException.ExceptionType.DAY_OFF,
                DoctorScheduleException.ExceptionType.VACATION,
            ]
        ).exists()

        if has_blocking_exception:
            self.summary["skipped_count"] += 1
            return

        schedules = DoctorWeeklySchedule.objects.filter(
            doctor=doctor,
            day_of_week=target_date.weekday(),
            is_active=True,
        )

        for schedule in schedules:
            self.generate_slots_for_weekly_schedule(schedule, target_date)

    def _create_slots(self, doctor, slot_date, start_time, end_time, generated_from):
        if not start_time or not end_time:
            self.summary["skipped_count"] += 1
            return []

        consultation_minutes = doctor.consultation_duration_minutes
        buffer_before_minutes = doctor.buffer_before_minutes
        buffer_after_minutes = doctor.buffer_after_minutes

        if consultation_minutes <= 0:
            raise ValueError("Consultation duration must be greater than zero.")

        gap_minutes = buffer_after_minutes + buffer_before_minutes
        slot_delta = timedelta(minutes=consultation_minutes)
        step_delta = timedelta(minutes=consultation_minutes + gap_minutes)

        window_start = self._make_aware(datetime.combine(slot_date, start_time))
        window_end = self._make_aware(datetime.combine(slot_date, end_time))

        created_slots = []
        current_start = window_start

        while current_start + slot_delta <= window_end:
            current_end = current_start + slot_delta
            slot, created = AppointmentSlot.objects.get_or_create(
                doctor=doctor,
                slot_date=slot_date,
                start_datetime=current_start,
                end_datetime=current_end,
                defaults={
                    "status": AppointmentSlot.Status.AVAILABLE,
                    "generated_from": generated_from,
                },
            )

            if created:
                created_slots.append(slot)
                self.summary["created_count"] += 1
            else:
                self.summary["skipped_count"] += 1

            current_start += step_delta

        return created_slots

    def _make_aware(self, value):
        if timezone.is_aware(value):
            return value

        return timezone.make_aware(value, timezone.get_current_timezone())
