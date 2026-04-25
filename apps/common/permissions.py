from rest_framework import permissions
from apps.appointments.models import Appointment


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user


class IsPatient(permissions.BasePermission):
    """
    Permission to check if user is a patient.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'patient_profile')
        )


class IsDoctor(permissions.BasePermission):
    """
    Permission to check if user is a doctor.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'doctor_profile')
        )


class IsReceptionist(permissions.BasePermission):
    """
    Permission to check if user is a receptionist.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'receptionist_profile')
        )


class IsAdmin(permissions.BasePermission):
    """
    Permission to check if user is an admin.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'admin_profile')
        )


class IsStaffUser(permissions.BasePermission):
    """
    Permission to check if user is staff (doctor, receptionist, or admin).
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return (
            hasattr(request.user, 'doctor_profile') or
            hasattr(request.user, 'receptionist_profile') or
            hasattr(request.user, 'admin_profile')
        )


class IsAppointmentOwner(permissions.BasePermission):
    """
    Permission to check if user owns the appointment (patient).
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Allow if user is the patient who owns the appointment
        if hasattr(request.user, 'patient_profile'):
            return obj.patient.user == request.user
        
        # Allow staff users (doctor, receptionist, admin)
        return IsStaffUser().has_permission(request, view)


class IsAppointmentDoctor(permissions.BasePermission):
    """
    Permission to check if user is the doctor assigned to the appointment.
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Allow if user is the doctor assigned to the appointment
        if hasattr(request.user, 'doctor_profile'):
            return obj.doctor.user == request.user
        
        # Allow admin users
        return IsAdmin().has_permission(request, view)


class CanManageAppointment(permissions.BasePermission):
    """
    Permission to check if user can manage the appointment.
    Patients can only manage their own appointments.
    Doctors can manage their assigned appointments.
    Receptionists and admins can manage all appointments.
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Patient can manage their own appointments
        if hasattr(request.user, 'patient_profile'):
            return obj.patient.user == request.user
        
        # Doctor can manage their assigned appointments
        if hasattr(request.user, 'doctor_profile'):
            return obj.doctor.user == request.user
        
        # Receptionist and admin can manage all appointments
        return IsReceptionist().has_permission(request, view) or IsAdmin().has_permission(request, view)


class CanViewAppointment(permissions.BasePermission):
    """
    Permission to check if user can view the appointment.
    Patients can view their own appointments.
    Doctors can view their assigned appointments.
    Receptionists and admins can view all appointments.
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Patient can view their own appointments
        if hasattr(request.user, 'patient_profile'):
            return obj.patient.user == request.user
        
        # Doctor can view their assigned appointments
        if hasattr(request.user, 'doctor_profile'):
            return obj.doctor.user == request.user
        
        # Receptionist and admin can view all appointments
        return IsReceptionist().has_permission(request, view) or IsAdmin().has_permission(request, view)


class CanBookAppointment(permissions.BasePermission):
    """
    Permission to check if user can book appointments.
    Patients can book appointments for themselves.
    Receptionists and admins can book appointments for any patient.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Patients can book for themselves
        if hasattr(request.user, 'patient_profile'):
            return True
        
        # Receptionist and admin can book for any patient
        return IsReceptionist().has_permission(request, view) or IsAdmin().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        # For booking, check if the patient is booking for themselves
        if hasattr(request.user, 'patient_profile'):
            return obj.patient.user == request.user
        
        # Staff can book for any patient
        return True


class CanManageSchedule(permissions.BasePermission):
    """
    Permission to check if user can manage doctor schedules.
    Only doctors (for their own schedule), receptionists, and admins can manage schedules.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return (
            IsDoctor().has_permission(request, view) or
            IsReceptionist().has_permission(request, view) or
            IsAdmin().has_permission(request, view)
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Doctor can manage their own schedule
        if hasattr(request.user, 'doctor_profile'):
            return obj.doctor.user == request.user
        
        # Receptionist and admin can manage any schedule
        return IsReceptionist().has_permission(request, view) or IsAdmin().has_permission(request, view)


class CanViewConsultationRecord(permissions.BasePermission):
    """
    Permission to check if user can view consultation records.
    Patients can view their own consultation records (summary only).
    Doctors can view consultation records for their patients.
    Admins can view all consultation records.
    Receptionists CANNOT view consultation records.
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Patient can view their own consultation records
        if hasattr(request.user, 'patient_profile'):
            return obj.appointment.patient.user == request.user
        
        # Doctor can view consultation records for their patients
        if hasattr(request.user, 'doctor_profile'):
            return obj.doctor.user == request.user
        
        # Admin can view all consultation records
        return IsAdmin().has_permission(request, view)


class CanManageConsultationRecord(permissions.BasePermission):
    """
    Permission to check if user can manage consultation records.
    Only doctors can create/edit consultation records for their patients.
    Admins can manage all consultation records.
    Patients and receptionists CANNOT manage consultation records.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return IsDoctor().has_permission(request, view) or IsAdmin().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Doctor can manage consultation records for their patients
        if hasattr(request.user, 'doctor_profile'):
            return obj.doctor.user == request.user
        
        # Admin can manage all consultation records
        return IsAdmin().has_permission(request, view)


class CanUpdateAppointmentStatus(permissions.BasePermission):
    """
    Permission to check if user can update appointment status.
    Patients can only cancel their own appointments (REQUESTED/CONFIRMED).
    Doctors can confirm, check-in, complete, cancel, and mark no-show for their appointments.
    Receptionists can confirm, check-in, cancel, and mark no-show.
    Admins can update any appointment status.
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Admin can update any appointment status
        if IsAdmin().has_permission(request, view):
            return True
        
        # Patient can only cancel their own appointments
        if hasattr(request.user, 'patient_profile'):
            if obj.patient.user != request.user:
                return False
            # Can only cancel if status is REQUESTED or CONFIRMED
            return obj.status in [Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED]
        
        # Doctor can manage their assigned appointments
        if hasattr(request.user, 'doctor_profile'):
            return obj.doctor.user == request.user
        
        # Receptionist can manage all appointments
        if hasattr(request.user, 'receptionist_profile'):
            return True
        
        return False


class CanRescheduleAppointment(permissions.BasePermission):
    """
    Permission to check if user can reschedule appointments.
    Patients can reschedule their own appointments (REQUESTED/CONFIRMED).
    Receptionists and admins can reschedule any appointment.
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Admin can reschedule any appointment
        if IsAdmin().has_permission(request, view):
            return True
        
        # Patient can reschedule their own appointments
        if hasattr(request.user, 'patient_profile'):
            if obj.patient.user != request.user:
                return False
            # Can only reschedule if status is REQUESTED or CONFIRMED
            return obj.status in [Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED]
        
        # Receptionist can reschedule any appointment
        if hasattr(request.user, 'receptionist_profile'):
            return True
        
        return False


class IsAuthenticatedOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """
    Custom permission that allows authenticated users to perform any action,
    but only allows read-only access for unauthenticated users.
    """
    pass
