from rest_framework import serializers
from datetime import date, datetime
from apps.accounts.models import DoctorProfile
from apps.accounts.serializers import DoctorProfileSerializer
from apps.scheduling.models import DoctorWeeklySchedule, DoctorScheduleException, AppointmentSlot


class DoctorWeeklyScheduleSerializer(serializers.ModelSerializer):
    doctor = DoctorProfileSerializer(read_only=True)
    doctor_id = serializers.IntegerField(write_only=True)
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = DoctorWeeklySchedule
        fields = [
            'id', 'doctor', 'doctor_id', 'day_of_week', 'day_of_week_display',
            'start_time', 'end_time', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate schedule time logic"""
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError("Start time must be before end time")
        return attrs


class DoctorScheduleExceptionSerializer(serializers.ModelSerializer):
    doctor = DoctorProfileSerializer(read_only=True)
    doctor_id = serializers.IntegerField(write_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = DoctorScheduleException
        fields = [
            'id', 'doctor', 'doctor_id', 'exception_date', 'type', 'type_display',
            'start_time', 'end_time', 'reason', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, attrs):
        """Validate exception logic"""
        exception_type = attrs.get('type')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if exception_type == DoctorScheduleException.ExceptionType.SPECIAL_WORKING_DAY:
            if not start_time or not end_time:
                raise serializers.ValidationError("Special working day requires start and end times")
            if start_time >= end_time:
                raise serializers.ValidationError("Start time must be before end time")
        elif exception_type in [DoctorScheduleException.ExceptionType.DAY_OFF, 
                              DoctorScheduleException.ExceptionType.VACATION]:
            if start_time or end_time:
                raise serializers.ValidationError("Day off and vacation should not have start/end times")
        
        return attrs


class AppointmentSlotSerializer(serializers.ModelSerializer):
    doctor = DoctorProfileSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    generated_from_display = serializers.CharField(source='get_generated_from_display', read_only=True)
    
    class Meta:
        model = AppointmentSlot
        fields = [
            'id', 'doctor', 'slot_date', 'start_datetime', 'end_datetime',
            'status', 'status_display', 'generated_from', 'generated_from_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppointmentSlotListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for slot listings"""
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AppointmentSlot
        fields = [
            'id', 'doctor_name', 'doctor_specialization', 'slot_date',
            'start_datetime', 'end_datetime', 'status', 'status_display'
        ]


class SlotGenerationRequestSerializer(serializers.Serializer):
    """Serializer for slot generation requests"""
    doctor_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    regenerate = serializers.BooleanField(default=False)
    
    def validate_doctor_id(self, value):
        """Validate doctor exists"""
        if not DoctorProfile.objects.filter(id=value).exists():
            raise serializers.ValidationError("Doctor does not exist")
        return value
    
    def validate(self, attrs):
        """Validate date range"""
        start_date = attrs['start_date']
        end_date = attrs['end_date']
        
        if start_date > end_date:
            raise serializers.ValidationError("Start date must be before end date")
        
        if start_date < date.today():
            raise serializers.ValidationError("Cannot generate slots for past dates")
        
        return attrs


class SlotAvailabilitySerializer(serializers.Serializer):
    """Serializer for checking slot availability"""
    doctor_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    
    def validate_doctor_id(self, value):
        """Validate doctor exists"""
        if not DoctorProfile.objects.filter(id=value).exists():
            raise serializers.ValidationError("Doctor does not exist")
        return value
    
    def validate(self, attrs):
        """Validate date range"""
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        return attrs
