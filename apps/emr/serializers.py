from rest_framework import serializers
from apps.accounts.models import DoctorProfile
from apps.accounts.serializers import DoctorProfileSerializer
from apps.emr.models import ConsultationRecord, PrescriptionItem, RequestedTest


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'drug_name', 'dose', 'duration', 'instructions', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RequestedTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestedTest
        fields = ['id', 'test_name', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConsultationRecordSerializer(serializers.ModelSerializer):
    doctor = DoctorProfileSerializer(read_only=True)
    prescription_items = PrescriptionItemSerializer(source='prescription_items', many=True, read_only=True)
    requested_tests = RequestedTestSerializer(source='requested_tests_normalized', many=True, read_only=True)
    
    # Write-only fields for creating consultation records
    doctor_id = serializers.IntegerField(write_only=True, required=False)
    prescription_items_data = PrescriptionItemSerializer(source='prescription_items', many=True, write_only=True, required=False)
    requested_tests_data = RequestedTestSerializer(source='requested_tests_normalized', many=True, write_only=True, required=False)
    
    class Meta:
        model = ConsultationRecord
        fields = [
            'id', 'appointment', 'doctor', 'doctor_id', 'diagnosis', 'notes',
            'requested_tests', 'summary_for_patient', 'created_at', 'updated_at',
            'prescription_items', 'prescription_items_data', 'requested_tests_data'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_appointment(self, value):
        """Validate that appointment is completed"""
        if value.status != 'COMPLETED':
            raise serializers.ValidationError("Consultation records can only be created for completed appointments")
        return value
    
    def create(self, validated_data):
        """Create consultation record with nested prescription items and tests"""
        prescription_items_data = validated_data.pop('prescription_items', [])
        requested_tests_data = validated_data.pop('requested_tests_normalized', [])
        
        consultation_record = ConsultationRecord.objects.create(**validated_data)
        
        # Create prescription items
        for item_data in prescription_items_data:
            PrescriptionItem.objects.create(
                consultation_record=consultation_record,
                **item_data
            )
        
        # Create requested tests
        for test_data in requested_tests_data:
            RequestedTest.objects.create(
                consultation_record=consultation_record,
                **test_data
            )
        
        return consultation_record


class ConsultationRecordCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating consultation records"""
    prescription_items = PrescriptionItemSerializer(many=True, required=False)
    requested_tests = RequestedTestSerializer(many=True, required=False)
    
    class Meta:
        model = ConsultationRecord
        fields = [
            'appointment', 'doctor', 'diagnosis', 'notes',
            'requested_tests', 'summary_for_patient',
            'prescription_items', 'requested_tests'
        ]
    
    def create(self, validated_data):
        """Create consultation record with nested items"""
        prescription_items_data = validated_data.pop('prescription_items', [])
        requested_tests_data = validated_data.pop('requested_tests', [])
        
        consultation_record = ConsultationRecord.objects.create(**validated_data)
        
        # Create prescription items
        for item_data in prescription_items_data:
            PrescriptionItem.objects.create(
                consultation_record=consultation_record,
                **item_data
            )
        
        # Create requested tests
        for test_data in requested_tests_data:
            RequestedTest.objects.create(
                consultation_record=consultation_record,
                **test_data
            )
        
        return consultation_record


class PatientConsultationRecordSerializer(serializers.ModelSerializer):
    """Serializer for patients viewing their consultation records (read-only)"""
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    prescription_items = PrescriptionItemSerializer(many=True, read_only=True)
    requested_tests = RequestedTestSerializer(many=True, read_only=True)
    
    class Meta:
        model = ConsultationRecord
        fields = [
            'id', 'doctor_name', 'doctor_specialization', 'diagnosis',
            'summary_for_patient', 'prescription_items', 'requested_tests',
            'created_at'
        ]
        read_only_fields = fields


class DoctorConsultationRecordSerializer(serializers.ModelSerializer):
    """Serializer for doctors managing consultation records"""
    prescription_items = PrescriptionItemSerializer(many=True, read_only=True)
    requested_tests = RequestedTestSerializer(many=True, read_only=True)
    
    class Meta:
        model = ConsultationRecord
        fields = [
            'id', 'appointment', 'doctor', 'diagnosis', 'notes',
            'requested_tests', 'summary_for_patient', 'prescription_items',
            'requested_tests', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
