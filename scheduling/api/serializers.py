from rest_framework import serializers
from django.utils import timezone

from scheduling.models import AppointmentSlot


class AppointmentSlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    specialization = serializers.CharField(source="doctor.specialization", read_only=True)
    consultation_fee = serializers.DecimalField(source="doctor.consultation_fee", max_digits=8, decimal_places=2, read_only=True)
    display_date = serializers.SerializerMethodField()
    display_time = serializers.SerializerMethodField()
    display_start = serializers.SerializerMethodField()
    display_end = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentSlot
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "specialization",
            "consultation_fee",
            "slot_date",
            "start_datetime",
            "end_datetime",
            "display_date",
            "display_time",
            "display_start",
            "display_end",
            "status",
            "generated_from",
        ]
        read_only_fields = fields

    def get_doctor_name(self, obj):
        first_name = (obj.doctor.user.first_name or "").strip()
        last_name = (obj.doctor.user.last_name or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        return full_name or obj.doctor.user.username

    def get_display_date(self, obj):
        return timezone.localtime(obj.start_datetime).strftime("%b %d, %Y")

    def get_display_time(self, obj):
        start = timezone.localtime(obj.start_datetime).strftime("%I:%M %p")
        end = timezone.localtime(obj.end_datetime).strftime("%I:%M %p")
        return f"{start} - {end}"

    def get_display_start(self, obj):
        return timezone.localtime(obj.start_datetime).strftime("%b %d, %Y %I:%M %p")

    def get_display_end(self, obj):
        return timezone.localtime(obj.end_datetime).strftime("%b %d, %Y %I:%M %p")
