from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# from django_filters.rest_framework import DjangoFilterBackend

from apps.emr.models import ConsultationRecord, PrescriptionItem, RequestedTest
from apps.emr.serializers import (
    ConsultationRecordSerializer, ConsultationRecordCreateSerializer,
    PatientConsultationRecordSerializer, DoctorConsultationRecordSerializer,
    PrescriptionItemSerializer, RequestedTestSerializer
)
from apps.common.permissions import CanViewConsultationRecord, CanManageConsultationRecord


class ConsultationRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for consultation record management.
    """
    queryset = ConsultationRecord.objects.all()
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['appointment', 'doctor']
    
    def get_serializer_class(self):
        user = self.request.user
        
        if self.action == 'create':
            return ConsultationRecordCreateSerializer
        elif hasattr(user, 'patient_profile'):
            return PatientConsultationRecordSerializer
        elif hasattr(user, 'doctor_profile'):
            return DoctorConsultationRecordSerializer
        else:
            return ConsultationRecordSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated, CanViewConsultationRecord]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, CanManageConsultationRecord]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Patients can only see their own consultation records
        if hasattr(user, 'patient_profile'):
            queryset = queryset.filter(appointment__patient=user.patient_profile)
        
        # Doctors can only see consultation records for their patients
        elif hasattr(user, 'doctor_profile'):
            queryset = queryset.filter(doctor=user.doctor_profile)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set doctor to current user if they are a doctor"""
        user = self.request.user
        if hasattr(user, 'doctor_profile'):
            serializer.save(doctor=user.doctor_profile)
        else:
            serializer.save()
    
    @action(detail=True, methods=['get'])
    def prescription_items(self, request, pk=None):
        """Get prescription items for a consultation record"""
        consultation_record = self.get_object()
        prescription_items = consultation_record.prescription_items.all()
        serializer = PrescriptionItemSerializer(prescription_items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def requested_tests(self, request, pk=None):
        """Get requested tests for a consultation record"""
        consultation_record = self.get_object()
        requested_tests = consultation_record.requested_tests_normalized.all()
        serializer = RequestedTestSerializer(requested_tests, many=True)
        return Response(serializer.data)
