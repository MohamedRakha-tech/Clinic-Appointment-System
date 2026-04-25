from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, datetime

from apps.scheduling.models import AppointmentSlot, DoctorWeeklySchedule, DoctorScheduleException
from apps.scheduling.serializers import (
    AppointmentSlotSerializer, AppointmentSlotListSerializer, SlotGenerationRequestSerializer,
    SlotAvailabilitySerializer, DoctorWeeklyScheduleSerializer, DoctorScheduleExceptionSerializer
)
from apps.scheduling.services import SlotGenerationService
from apps.common.permissions import IsStaffUser, CanManageSchedule


class AppointmentSlotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing appointment slots.
    """
    queryset = AppointmentSlot.objects.all()
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['doctor', 'slot_date', 'status']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AppointmentSlotListSerializer
        return AppointmentSlotSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsStaffUser]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available slots for filtering"""
        doctor_id = request.query_params.get('doctor_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not all([doctor_id, start_date, end_date]):
            return Response(
                {'error': 'doctor_id, start_date, and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=doctor_id)
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            slots = SlotGenerationService.get_available_slots(doctor, start_date, end_date)
            serializer = AppointmentSlotListSerializer(slots, many=True)
            return Response(serializer.data)
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)


class DoctorWeeklyScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctor weekly schedules.
    """
    queryset = DoctorWeeklySchedule.objects.all()
    serializer_class = DoctorWeeklyScheduleSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['doctor', 'day_of_week', 'is_active']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated, CanManageSchedule]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Doctors can only see their own schedules
        if hasattr(user, 'doctor_profile'):
            queryset = queryset.filter(doctor=user.doctor_profile)
        
        return queryset


class DoctorScheduleExceptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing doctor schedule exceptions.
    """
    queryset = DoctorScheduleException.objects.all()
    serializer_class = DoctorScheduleExceptionSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['doctor', 'exception_date', 'type']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated, CanManageSchedule]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Doctors can only see their own exceptions
        if hasattr(user, 'doctor_profile'):
            queryset = queryset.filter(doctor=user.doctor_profile)
        
        return queryset


class SlotGenerationViewSet(viewsets.ViewSet):
    """
    ViewSet for slot generation operations.
    """
    permission_classes = [IsAuthenticated, CanManageSchedule]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate slots for a date range"""
        serializer = SlotGenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=serializer.validated_data['doctor_id'])
            
            slots = SlotGenerationService.generate_slots_for_date_range(
                doctor=doctor,
                start_date=serializer.validated_data['start_date'],
                end_date=serializer.validated_data['end_date'],
                regenerate=serializer.validated_data['regenerate']
            )
            
            return Response({
                'message': f'Generated {len(slots)} slots',
                'slots_count': len(slots)
            })
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        """Check slot availability for a date range"""
        serializer = SlotAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=serializer.validated_data['doctor_id'])
            
            available_slots = SlotGenerationService.get_available_slots(
                doctor=doctor,
                start_date=serializer.validated_data['start_date'],
                end_date=serializer.validated_data['end_date']
            )
            
            slot_serializer = AppointmentSlotListSerializer(available_slots, many=True)
            return Response({
                'available_slots': slot_serializer.data,
                'count': len(available_slots)
            })
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
