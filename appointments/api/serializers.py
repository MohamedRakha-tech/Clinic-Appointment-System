from rest_framework import serializers

from appointments.models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    doctor_specialization = serializers.CharField(source="doctor.specialization", read_only=True)
    slot_status = serializers.CharField(source="slot.status", read_only=True)
    consultation_summary = serializers.SerializerMethodField()
    can_view_medical_summary = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "appointment_code",
            "patient",
            "patient_name",
            "doctor",
            "doctor_name",
            "doctor_specialization",
            "slot",
            "slot_status",
            "scheduled_start",
            "scheduled_end",
            "status",
            "booking_source",
            "notes_for_staff",
            "consultation_summary",
            "can_view_medical_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_patient_name(self, obj):
        first_name = (obj.patient.user.first_name or "").strip()
        last_name = (obj.patient.user.last_name or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        return full_name or obj.patient.user.username

    def get_doctor_name(self, obj):
        first_name = (obj.doctor.user.first_name or "").strip()
        last_name = (obj.doctor.user.last_name or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        return full_name or obj.doctor.user.username

    def get_consultation_summary(self, obj):
        consultation = getattr(obj, "consultation_record", None)
        if not consultation:
            return None

        request = self.context.get("request")
        if request and hasattr(request.user, "patient_profile"):
            if obj.patient_id != request.user.patient_profile.id:
                return None

        return consultation.summary_for_patient

    def get_can_view_medical_summary(self, obj):
        consultation = getattr(obj, "consultation_record", None)
        return consultation is not None and obj.status == Appointment.Status.COMPLETED


class AppointmentCreateSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField()
    patient_id = serializers.IntegerField(required=False, allow_null=True)
    notes_for_staff = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class AppointmentActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    slot_id = serializers.IntegerField(required=False)
