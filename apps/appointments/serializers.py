from rest_framework import serializers
from django.utils import timezone
from apps.accounts.models import User, PatientProfile, DoctorProfile
from apps.accounts.serializers import UserSerializer, PatientProfileSerializer, DoctorProfileSerializer
from apps.appointments.models import Appointment, AppointmentStatusHistory, AppointmentRescheduleHistory
from apps.scheduling.models import AppointmentSlot
from apps.scheduling.serializers import AppointmentSlotSerializer
from apps.emr.models import ConsultationRecord
from apps.emr.serializers import ConsultationRecordSerializer, PrescriptionItemSerializer, RequestedTestSerializer


class AppointmentStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = AppointmentStatusHistory
        fields = ['id', 'old_status', 'new_status', 'changed_by', 'change_reason', 'created_at']
        read_only_fields = ['id', 'created_at']


class AppointmentRescheduleHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = AppointmentRescheduleHistory
        fields = [
            'id', 'old_start_datetime', 'old_end_datetime', 
            'new_start_datetime', 'new_end_datetime', 'changed_by', 
            'reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    doctor = DoctorProfileSerializer(read_only=True)
    slot = AppointmentSlotSerializer(read_only=True)
    confirmed_by = UserSerializer(read_only=True)
    checked_in_by = UserSerializer(read_only=True)
    cancelled_by = UserSerializer(read_only=True)
    status_history = AppointmentStatusHistorySerializer(source='status_history', many=True, read_only=True)
    reschedule_history = AppointmentRescheduleHistorySerializer(source='reschedule_history', many=True, read_only=True)
    consultation_record = ConsultationRecordSerializer(read_only=True)
    
    # Write-only fields for creating appointments
    patient_id = serializers.IntegerField(write_only=True)
    doctor_id = serializers.IntegerField(write_only=True)
    slot_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_code', 'patient', 'doctor', 'slot',
            'scheduled_start', 'scheduled_end', 'status', 'booking_source',
            'confirmed_by', 'checked_in_by', 'cancelled_by', 
            'cancellation_reason', 'notes_for_staff', 'created_at', 'updated_at',
            'patient_id', 'doctor_id', 'slot_id',
            'status_history', 'reschedule_history', 'consultation_record'
        ]
        read_only_fields = [
            'id', 'appointment_code', 'scheduled_start', 'scheduled_end',
            'confirmed_by', 'checked_in_by', 'cancelled_by', 'created_at', 'updated_at'
        ]
    
    def validate_slot_id(self, value):
        """Validate that the slot exists and is available"""
        try:
            slot = AppointmentSlot.objects.get(id=value)
            if slot.status != AppointmentSlot.Status.AVAILABLE:
                raise serializers.ValidationError("Slot is not available for booking")
            return value
        except AppointmentSlot.DoesNotExist:
            raise serializers.ValidationError("Slot does not exist")
    
    def validate(self, attrs):
        """Validate appointment booking rules"""
        # Get objects from IDs
        try:
            patient = PatientProfile.objects.get(id=attrs['patient_id'])
            doctor = DoctorProfile.objects.get(id=attrs['doctor_id'])
            slot = AppointmentSlot.objects.get(id=attrs['slot_id'])
        except (PatientProfile.DoesNotExist, DoctorProfile.DoesNotExist, AppointmentSlot.DoesNotExist):
            raise serializers.ValidationError("Invalid patient, doctor, or slot")
        
        # Validate slot belongs to the specified doctor
        if slot.doctor != doctor:
            raise serializers.ValidationError("Slot does not belong to the specified doctor")
        
        # Check for patient overlapping appointments
        overlapping = Appointment.objects.filter(
            patient=patient,
            status__in=[Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED, 
                       Appointment.Status.CHECKED_IN],
        ).filter(
            scheduled_start__lt=slot.end_datetime,
            scheduled_end__gt=slot.start_datetime
        ).exists()
        
        if overlapping:
            raise serializers.ValidationError("Patient has an overlapping appointment")
        
        return attrs


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating appointments"""
    
    class Meta:
        model = Appointment
        fields = ['patient_id', 'doctor_id', 'slot_id', 'booking_source', 'notes_for_staff']
    
    def create(self, validated_data):
        """Create appointment using the booking service"""
        from apps.appointments.services import AppointmentBookingService
        
        patient = PatientProfile.objects.get(id=validated_data['patient_id'])
        doctor = DoctorProfile.objects.get(id=validated_data['doctor_id'])
        slot = AppointmentSlot.objects.get(id=validated_data['slot_id'])
        
        appointment, _ = AppointmentBookingService.book_appointment(
            patient=patient,
            doctor=doctor,
            slot=slot,
            booking_source=validated_data.get('booking_source', Appointment.BookingSource.PATIENT),
            notes_for_staff=validated_data.get('notes_for_staff'),
            booked_by=self.context['request'].user
        )
        
        return appointment


class AppointmentStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating appointment status"""
    status = serializers.ChoiceField(choices=Appointment.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Validate status update"""
        appointment = self.context['appointment']
        new_status = attrs['status']
        user = self.context['request'].user
        
        # Validate status transition using the service
        from apps.appointments.services import AppointmentStatusService
        try:
            AppointmentStatusService._validate_status_transition(
                appointment.status, new_status, user, appointment
            )
        except Exception as e:
            raise serializers.ValidationError(str(e))
        
        return attrs


class AppointmentRescheduleSerializer(serializers.Serializer):
    """Serializer for rescheduling appointments"""
    new_slot_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=255)
    
    def validate_new_slot_id(self, value):
        """Validate the new slot"""
        try:
            slot = AppointmentSlot.objects.get(id=value)
            if slot.status != AppointmentSlot.Status.AVAILABLE:
                raise serializers.ValidationError("New slot is not available")
            return value
        except AppointmentSlot.DoesNotExist:
            raise serializers.ValidationError("New slot does not exist")
    
    def validate(self, attrs):
        """Validate rescheduling request"""
        appointment = self.context['appointment']
        new_slot = AppointmentSlot.objects.get(id=attrs['new_slot_id'])
        
        # Ensure new slot belongs to the same doctor
        if new_slot.doctor != appointment.doctor:
            raise serializers.ValidationError("New slot must belong to the same doctor")
        
        # Check for patient overlapping appointments (excluding current appointment)
        overlapping = Appointment.objects.filter(
            patient=appointment.patient,
            status__in=[Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED, 
                       Appointment.Status.CHECKED_IN],
        ).exclude(id=appointment.id).filter(
            scheduled_start__lt=new_slot.end_datetime,
            scheduled_end__gt=new_slot.start_datetime
        ).exists()
        
        if overlapping:
            raise serializers.ValidationError("Patient has an overlapping appointment with the new slot")
        
        return attrs


class AppointmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for appointment lists"""
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_code', 'patient_name', 'doctor_name', 
            'doctor_specialization', 'scheduled_start', 'scheduled_end', 
            'status', 'booking_source'
        ]


class PatientAppointmentSerializer(serializers.ModelSerializer):
    """Serializer for patients viewing their own appointments"""
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    consultation_summary = serializers.CharField(source='consultation_record.summary_for_patient', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_code', 'doctor_name', 'doctor_specialization',
            'scheduled_start', 'scheduled_end', 'status', 'booking_source',
            'notes_for_staff', 'consultation_summary', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class DoctorAppointmentSerializer(serializers.ModelSerializer):
    """Serializer for doctors viewing their appointments"""
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    patient_dob = serializers.DateField(source='patient.date_of_birth', read_only=True)
    consultation_record = ConsultationRecordSerializer(read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_code', 'patient_name', 'patient_dob',
            'scheduled_start', 'scheduled_end', 'status', 'booking_source',
            'notes_for_staff', 'consultation_record', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class StaffAppointmentSerializer(serializers.ModelSerializer):
    """Serializer for receptionists and admins viewing appointments"""
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.user.phone', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_code', 'patient_name', 'patient_phone',
            'doctor_name', 'scheduled_start', 'scheduled_end', 'status',
            'booking_source', 'confirmed_by', 'checked_in_by', 'cancelled_by',
            'cancellation_reason', 'notes_for_staff', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
