from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
# from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.models import User, PatientProfile, DoctorProfile, ReceptionistProfile, AdminProfile
from apps.accounts.serializers import (
    UserSerializer, UserCreateSerializer, PatientProfileSerializer, PatientProfileCreateSerializer,
    DoctorProfileSerializer, DoctorProfileCreateSerializer, UserProfileSerializer
)
from apps.common.permissions import IsAdmin, IsStaffUser


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.
    """
    queryset = User.objects.all()
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['is_active', 'is_staff']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [AllowAny]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAdmin]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user's profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class PatientProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for patient profile management.
    """
    queryset = PatientProfile.objects.all()
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['user']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PatientProfileCreateSerializer
        return PatientProfileSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsStaffUser]
        elif self.action == 'create':
            self.permission_classes = [IsAdmin]
        else:
            self.permission_classes = [IsAdmin]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Patients can only see their own profile
        if hasattr(user, 'patient_profile'):
            queryset = queryset.filter(user=user)
        
        return queryset


class DoctorProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for doctor profile management.
    """
    queryset = DoctorProfile.objects.all()
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['user', 'specialization']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DoctorProfileCreateSerializer
        return DoctorProfileSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        elif self.action == 'create':
            self.permission_classes = [IsAdmin]
        else:
            self.permission_classes = [IsAdmin]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Doctors can only see their own profile
        if hasattr(user, 'doctor_profile'):
            queryset = queryset.filter(user=user)
        
        return queryset
