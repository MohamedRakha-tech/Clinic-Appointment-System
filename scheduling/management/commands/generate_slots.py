from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.models import DoctorProfile
from scheduling.services import SlotGenerationService


class Command(BaseCommand):
    help = "Generate appointment slots from doctor weekly schedules and exceptions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Generate slots from today through today plus this number of days.",
        )
        parser.add_argument(
            "--doctor-id",
            type=int,
            help="Generate slots for one doctor profile ID.",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date in YYYY-MM-DD format.",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="End date in YYYY-MM-DD format.",
        )

    def handle(self, *args, **options):
        start_date, end_date = self._get_date_range(options)
        service = SlotGenerationService()

        doctor_id = options.get("doctor_id")
        if doctor_id:
            try:
                doctor = DoctorProfile.objects.get(pk=doctor_id)
            except DoctorProfile.DoesNotExist as exc:
                raise CommandError(f"DoctorProfile with id {doctor_id} was not found.") from exc

            summary = service.generate_slots_for_doctor(doctor, start_date, end_date)
        else:
            summary = service.generate_slots_for_all_doctors(start_date, end_date)

        self.stdout.write(self.style.SUCCESS("Slot generation completed."))
        self.stdout.write(f"Doctors processed: {summary['doctors_processed']}")
        self.stdout.write(f"Slots created: {summary['created_count']}")
        self.stdout.write(f"Slots skipped: {summary['skipped_count']}")
        self.stdout.write(f"Errors: {len(summary['errors'])}")

        for error in summary["errors"]:
            self.stdout.write(self.style.ERROR(f"- {error}"))

    def _get_date_range(self, options):
        start_date_value = options.get("start_date")
        end_date_value = options.get("end_date")

        if start_date_value or end_date_value:
            if not start_date_value or not end_date_value:
                raise CommandError("--start-date and --end-date must be provided together.")

            start_date = parse_date(start_date_value)
            end_date = parse_date(end_date_value)

            if not start_date or not end_date:
                raise CommandError("Dates must use YYYY-MM-DD format.")
        else:
            days = options["days"]
            if days < 0:
                raise CommandError("--days must be 0 or greater.")

            start_date = timezone.localdate()
            end_date = start_date + timedelta(days=days)

        if start_date > end_date:
            raise CommandError("Start date must be before or equal to end date.")

        return start_date, end_date
