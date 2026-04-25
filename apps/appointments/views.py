from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, datetime

from apps.appointments.models import Appointment, AppointmentStatusHistory, AppointmentRescheduleHistory
from apps.appointments.services import (
    AppointmentBookingService, AppointmentStatusService, 
    AppointmentRescheduleService, AppointmentOverlapService
)
from apps.scheduling.models import AppointmentSlot


@login_required
def appointment_list(request):
    """List appointments based on user role"""
    user = request.user
    queryset = Appointment.objects.all()
    
    # Filter appointments based on user role
    if hasattr(user, 'patient_profile'):
        queryset = queryset.filter(patient=user.patient_profile)
    elif hasattr(user, 'doctor_profile'):
        queryset = queryset.filter(doctor=user.doctor_profile)
    elif not (hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile')):
        queryset = queryset.none()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Order by scheduled start time
    queryset = queryset.order_by('-scheduled_start')
    
    context = {
        'appointments': queryset,
        'status_choices': Appointment.Status.choices,
        'current_status': status_filter,
        'user_role': _get_user_role(user)
    }
    
    return render(request, 'appointments/appointment_list.html', context)


@login_required
def appointment_detail(request, pk):
    """View appointment details"""
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Check permissions
    if not _can_view_appointment(request.user, appointment):
        messages.error(request, "You don't have permission to view this appointment.")
        return redirect('appointments:appointment_list')
    
    # Get history
    status_history = AppointmentStatusHistory.objects.filter(
        appointment=appointment
    ).order_by('created_at')
    
    reschedule_history = AppointmentRescheduleHistory.objects.filter(
        appointment=appointment
    ).order_by('created_at')
    
    context = {
        'appointment': appointment,
        'status_history': status_history,
        'reschedule_history': reschedule_history,
        'user_role': _get_user_role(request.user)
    }
    
    return render(request, 'appointments/appointment_detail.html', context)


@login_required
def book_appointment(request):
    """Book a new appointment"""
    if request.method == 'POST':
        slot_id = request.POST.get('slot_id')
        notes = request.POST.get('notes', '')
        
        if not slot_id:
            messages.error(request, "Please select a time slot.")
            return redirect('appointments:book_appointment')
        
        try:
            slot = AppointmentSlot.objects.get(id=slot_id)
            
            # Get patient profile
            if hasattr(request.user, 'patient_profile'):
                patient = request.user.patient_profile
            else:
                messages.error(request, "Only patients can book appointments.")
                return redirect('appointments:book_appointment')
            
            # Book appointment
            appointment, success = AppointmentBookingService.book_appointment(
                patient=patient,
                doctor=slot.doctor,
                slot=slot,
                notes=notes
            )
            
            if success:
                messages.success(request, f"Appointment booked successfully! Code: {appointment.appointment_code}")
                return redirect('appointments:appointment_detail', pk=appointment.pk)
            else:
                messages.error(request, "Failed to book appointment. Please try again.")
                
        except AppointmentSlot.DoesNotExist:
            messages.error(request, "Selected slot not available.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    # Get available slots
    available_slots = AppointmentSlot.objects.filter(
        status=AppointmentSlot.Status.AVAILABLE,
        start_datetime__gte=timezone.now()
    ).order_by('start_datetime')[:20]  # Limit to next 20 slots
    
    context = {
        'available_slots': available_slots,
        'user_role': _get_user_role(request.user)
    }
    
    return render(request, 'appointments/book_appointment.html', context)


@login_required
def update_appointment_status(request, pk, action):
    """Update appointment status"""
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Check permissions
    if not _can_update_status(request.user, appointment, action):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('appointments:appointment_detail', pk=appointment.pk)
    
    try:
        if action == 'confirm':
            new_status = Appointment.Status.CONFIRMED
            reason = "Confirmed by staff"
        elif action == 'check_in':
            new_status = Appointment.Status.CHECKED_IN
            reason = "Patient checked in"
        elif action == 'complete':
            new_status = Appointment.Status.COMPLETED
            reason = "Appointment completed"
        elif action == 'cancel':
            new_status = Appointment.Status.CANCELLED
            reason = request.POST.get('reason', 'Appointment cancelled')
        elif action == 'no_show':
            new_status = Appointment.Status.NO_SHOW
            reason = "Patient did not show up"
        else:
            messages.error(request, "Invalid action.")
            return redirect('appointments:appointment_detail', pk=appointment.pk)
        
        updated_appointment, success = AppointmentStatusService.update_appointment_status(
            appointment=appointment,
            new_status=new_status,
            changed_by=request.user,
            reason=reason
        )
        
        if success:
            messages.success(request, f"Appointment {action.replace('_', ' ')} successfully.")
        else:
            messages.error(request, f"Failed to {action.replace('_', ' ')} appointment.")
            
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    
    return redirect('appointments:appointment_detail', pk=appointment.pk)


@login_required
def reschedule_appointment(request, pk):
    """Reschedule an appointment"""
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Check permissions
    if not AppointmentRescheduleService.can_reschedule(appointment, request.user):
        messages.error(request, "You cannot reschedule this appointment.")
        return redirect('appointments:appointment_detail', pk=appointment.pk)
    
    if request.method == 'POST':
        new_slot_id = request.POST.get('new_slot_id')
        reason = request.POST.get('reason', 'Rescheduled')
        
        if not new_slot_id:
            messages.error(request, "Please select a new time slot.")
            return redirect('appointments:reschedule_appointment', pk=appointment.pk)
        
        try:
            updated_appointment, success = AppointmentRescheduleService.reschedule_appointment(
                appointment=appointment,
                new_slot_id=new_slot_id,
                reason=reason,
                changed_by=request.user
            )
            
            if success:
                messages.success(request, "Appointment rescheduled successfully.")
                return redirect('appointments:appointment_detail', pk=appointment.pk)
            else:
                messages.error(request, "Failed to reschedule appointment.")
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    # Get available slots for the same doctor
    available_slots = AppointmentSlot.objects.filter(
        doctor=appointment.doctor,
        status=AppointmentSlot.Status.AVAILABLE,
        start_datetime__gte=timezone.now()
    ).exclude(id=appointment.slot.id).order_by('start_datetime')[:20]
    
    context = {
        'appointment': appointment,
        'available_slots': available_slots,
        'user_role': _get_user_role(request.user)
    }
    
    return render(request, 'appointments/reschedule_appointment.html', context)


@login_required
def search_appointments(request):
    """Search appointments (staff only)"""
    if not (hasattr(request.user, 'receptionist_profile') or hasattr(request.user, 'admin_profile')):
        messages.error(request, "Permission denied.")
        return redirect('appointments:appointment_list')
    
    query = request.GET.get('q', '')
    queryset = Appointment.objects.all()
    
    if query:
        queryset = queryset.filter(
            appointment_code__icontains=query
        ) | queryset.filter(
            patient__user__first_name__icontains=query
        ) | queryset.filter(
            patient__user__last_name__icontains=query
        )
    
    queryset = queryset.order_by('-scheduled_start')
    
    context = {
        'appointments': queryset,
        'query': query,
        'user_role': _get_user_role(request.user)
    }
    
    return render(request, 'appointments/search_results.html', context)


# Helper functions
def _get_user_role(user):
    """Get user role for template context"""
    if hasattr(user, 'patient_profile'):
        return 'patient'
    elif hasattr(user, 'doctor_profile'):
        return 'doctor'
    elif hasattr(user, 'receptionist_profile'):
        return 'receptionist'
    elif hasattr(user, 'admin_profile'):
        return 'admin'
    return 'unknown'


def _can_view_appointment(user, appointment):
    """Check if user can view appointment"""
    if hasattr(user, 'patient_profile'):
        return appointment.patient == user.patient_profile
    elif hasattr(user, 'doctor_profile'):
        return appointment.doctor == user.doctor_profile
    elif hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile'):
        return True
    return False


def _can_update_status(user, appointment, action):
    """Check if user can update appointment status"""
    if action == 'confirm':
        return hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile')
    elif action == 'check_in':
        return hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile')
    elif action == 'complete':
        return hasattr(user, 'doctor_profile') or hasattr(user, 'admin_profile')
    elif action == 'cancel':
        if hasattr(user, 'patient_profile'):
            return appointment.patient == user.patient_profile and appointment.status in [
                Appointment.Status.REQUESTED, Appointment.Status.CONFIRMED
            ]
        return hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile')
    elif action == 'no_show':
        return hasattr(user, 'doctor_profile') or hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile')
    return False
