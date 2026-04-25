from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import date, datetime

from apps.queueing.services import QueueManagementService
from apps.appointments.serializers import AppointmentListSerializer
from apps.common.permissions import IsStaffUser, IsDoctor, IsReceptionist


class QueueViewSet(viewsets.ViewSet):
    """
    ViewSet for queue management operations.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def doctor_queue(self, request):
        """Get current queue for a doctor"""
        doctor_id = request.query_params.get('doctor_id')
        target_date = request.query_params.get('date')
        
        if not doctor_id:
            return Response(
                {'error': 'doctor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=doctor_id)
            
            # Check permissions
            user = request.user
            if hasattr(user, 'doctor_profile') and user.doctor_profile != doctor:
                return Response(
                    {'error': 'Can only view own queue'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if target_date:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            queue = QueueManagementService.get_doctor_queue(doctor, target_date)
            serializer = AppointmentListSerializer(queue, many=True)
            
            return Response({
                'queue': serializer.data,
                'count': len(queue)
            })
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def waiting_room(self, request):
        """Get waiting room queue for a doctor"""
        doctor_id = request.query_params.get('doctor_id')
        
        if not doctor_id:
            return Response(
                {'error': 'doctor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=doctor_id)
            
            # Check permissions
            user = request.user
            if hasattr(user, 'doctor_profile') and user.doctor_profile != doctor:
                return Response(
                    {'error': 'Can only view own waiting room'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            waiting_queue = QueueManagementService.get_waiting_room_queue(doctor)
            
            return Response({
                'waiting_room': waiting_queue,
                'count': len(waiting_queue)
            })
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def today_schedule(self, request):
        """Get today's schedule for a doctor"""
        doctor_id = request.query_params.get('doctor_id')
        
        if not doctor_id:
            return Response(
                {'error': 'doctor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=doctor_id)
            
            # Check permissions
            user = request.user
            if hasattr(user, 'doctor_profile') and user.doctor_profile != doctor:
                return Response(
                    {'error': 'Can only view own schedule'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            schedule = QueueManagementService.get_today_schedule(doctor)
            
            return Response(schedule)
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get queue overview for receptionists"""
        if not IsReceptionist().has_permission(request, self) and not IsDoctor().has_permission(request, self):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        overview = QueueManagementService.get_overview_for_receptionist()
        return Response(overview)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get queue statistics for a doctor"""
        doctor_id = request.query_params.get('doctor_id')
        date_range = request.query_params.get('days', 7)
        
        if not doctor_id:
            return Response(
                {'error': 'doctor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_range = int(date_range)
        except ValueError:
            date_range = 7
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=doctor_id)
            
            # Check permissions
            user = request.user
            if hasattr(user, 'doctor_profile') and user.doctor_profile != doctor:
                return Response(
                    {'error': 'Can only view own statistics'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            stats = QueueManagementService.get_queue_statistics(doctor, date_range)
            return Response(stats)
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def estimate_wait_time(self, request):
        """Estimate wait time for a doctor"""
        doctor_id = request.query_params.get('doctor_id')
        
        if not doctor_id:
            return Response(
                {'error': 'doctor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=doctor_id)
            
            wait_time = QueueManagementService.estimate_wait_time(doctor)
            
            return Response({
                'estimated_wait_time_minutes': wait_time,
                'has_queue': wait_time is not None
            })
        except DoctorProfile.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)


class CheckInViewSet(viewsets.ViewSet):
    """
    ViewSet for patient check-in operations.
    """
    permission_classes = [IsAuthenticated, IsReceptionist]
    
    @action(detail=False, methods=['post'])
    def patient(self, request):
        """Check in a patient"""
        appointment_id = request.data.get('appointment_id')
        notes = request.data.get('notes', '')
        
        if not appointment_id:
            return Response(
                {'error': 'appointment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.appointments.models import Appointment
            appointment = Appointment.objects.get(id=appointment_id)
            
            checked_in_appointment, success = QueueManagementService.check_in_patient(
                appointment=appointment,
                checked_in_by=request.user,
                notes=notes
            )
            
            if success:
                from apps.appointments.serializers import AppointmentSerializer
                serializer = AppointmentSerializer(checked_in_appointment, context={'request': request})
                return Response(serializer.data)
            else:
                return Response(
                    {'error': 'Failed to check in patient'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
