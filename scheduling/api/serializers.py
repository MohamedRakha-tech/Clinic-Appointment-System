from rest_framework import serializers

from scheduling.models import AppointmentSlot


class AppointmentSlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    specialization = serializers.CharField(source="doctor.specialization", read_only=True)

    class Meta:
        model = AppointmentSlot
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "specialization",
            "slot_date",
            "start_datetime",
            "end_datetime",
            "status",
            "generated_from",
        ]
        read_only_fields = fields

    def get_doctor_name(self, obj):
        first_name = (obj.doctor.user.first_name or "").strip()
        last_name = (obj.doctor.user.last_name or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        return full_name or obj.doctor.user.username

