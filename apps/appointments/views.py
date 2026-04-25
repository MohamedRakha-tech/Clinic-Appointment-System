from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, datetime, timedelta

from apps.appointments.models import Appointment, AppointmentStatusHistory, AppointmentRescheduleHistory
from apps.appointments.services import (
    AppointmentBookingService, AppointmentStatusService, 
    AppointmentRescheduleService, AppointmentOverlapService
)
from apps.scheduling.models import AppointmentSlot
from apps.accounts.models import DoctorProfile, PatientProfile


# @login_required
def appointment_list(request):
    """List appointments based on user role"""
    user = request.user
    base_queryset = Appointment.objects.all()
    
    # Filter appointments based on user role
    if hasattr(user, 'patient_profile'):
        base_queryset = base_queryset.filter(patient=user.patient_profile)
    elif hasattr(user, 'doctor_profile'):
        base_queryset = base_queryset.filter(doctor=user.doctor_profile)
    elif not (hasattr(user, 'receptionist_profile') or hasattr(user, 'admin_profile')):
        base_queryset = base_queryset.none()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        base_queryset = base_queryset.filter(status=status_filter)
    
    # Order by scheduled start time
    queryset = base_queryset.order_by('-scheduled_start')
    
    # Prepare tab data
    tabs = {
        'all': 'All',
        'upcoming': 'Upcoming',
        'past': 'Past',
        'cancelled': 'Cancelled'
    }
    
    # Calculate tab counts
    tab_counts = {
        'all': base_queryset.count(),
        'upcoming': base_queryset.filter(scheduled_start__gte=timezone.now()).exclude(status='CANCELLED').count(),
        'past': base_queryset.filter(scheduled_start__lt=timezone.now(), status='COMPLETED').count(),
        'cancelled': base_queryset.filter(status='CANCELLED').count()
    }
    
    # Determine active tab
    active_tab = request.GET.get('tab', 'all')
    
    # Apply tab filtering
    if active_tab == 'upcoming':
        queryset = base_queryset.filter(scheduled_start__gte=timezone.now()).exclude(status='CANCELLED')
    elif active_tab == 'past':
        queryset = base_queryset.filter(scheduled_start__lt=timezone.now(), status='COMPLETED')
    elif active_tab == 'cancelled':
        queryset = base_queryset.filter(status='CANCELLED')
    else:  # 'all'
        queryset = base_queryset
    
    # Apply status filter if provided
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    queryset = queryset.order_by('-scheduled_start')
    
    context = {
        'appointments': queryset,
        'tabs': tabs.items(),
        'tab_counts': tab_counts,
        'active_tab': active_tab,
        'status_choices': Appointment.Status.choices,
        'current_status': status_filter,
        'user_role': _get_user_role(user)
    }
    
    return render(request, 'appointments/list.html', context)


# @login_required
def appointment_detail(request, pk):
    """View appointment details"""
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # For testing without auth, skip permission check
    # if not _can_view_appointment(request.user, appointment):
    #     messages.error(request, "You don't have permission to view this appointment.")
    #     return redirect('appointments:appointment_list')
    
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
    
    return render(request, 'appointments/detail.html', context)


# @login_required
def book_appointment(request):
    """Book a new appointment with multi-step process"""
    # For testing without auth, create or get a mock patient
    if not hasattr(request.user, 'patient_profile') or not request.user.is_authenticated:
        # Get first patient for testing, or create a mock one
        from apps.accounts.models import PatientProfile
        patient = PatientProfile.objects.first()
        if not patient:
            # Create a mock user and patient if none exists
            from django.contrib.auth import get_user_model
            User = get_user_model()
            mock_user = User.objects.create_user(
                username='test_patient',
                email='test@clinic.com',
                first_name='Test',
                last_name='Patient'
            )
            patient = PatientProfile.objects.create(
                user=mock_user,
                date_of_birth='1990-01-01'
            )
        # Set a mock user role for template
        request.user = patient.user
    else:
        patient = request.user.patient_profile
    
    # Initialize session variables for booking process
    if 'booking_data' not in request.session:
        request.session['booking_data'] = {}
    
    booking_data = request.session['booking_data']
    
    # Define booking steps
    steps = [(1, 'Doctor'), (2, 'Date'), (3, 'Time'), (4, 'Confirm')]
    
    # Handle form submissions
    if request.method == 'POST':
        step = int(request.POST.get('step', 1))
        
        if step == 1:
            # Step 1: Doctor selection
            doctor_id = request.POST.get('doctor_id')
            if doctor_id:
                try:
                    doctor = DoctorProfile.objects.get(id=doctor_id)
                    booking_data['doctor_id'] = doctor_id
                    booking_data['doctor_name'] = f"Dr. {doctor.user.first_name} {doctor.user.last_name}"
                    request.session['booking_data'] = booking_data
                    return redirect('appointments:book_appointment')
                except DoctorProfile.DoesNotExist:
                    messages.error(request, "Invalid doctor selection.")
            else:
                messages.error(request, "Please select a doctor.")
        
        elif step == 2:
            # Step 2: Date selection
            selected_date = request.POST.get('selected_date')
            if selected_date:
                booking_data['selected_date'] = selected_date
                request.session['booking_data'] = booking_data
                return redirect('appointments:book_appointment')
            else:
                messages.error(request, "Please select a date.")
        
        elif step == 3:
            # Step 3: Time slot selection
            slot_id = request.POST.get('slot_id')
            if slot_id:
                try:
                    slot = AppointmentSlot.objects.get(id=slot_id)
                    booking_data['slot_id'] = slot_id
                    booking_data['slot_time'] = slot.start_datetime.strftime('%I:%M %p')
                    request.session['booking_data'] = booking_data
                    return redirect('appointments:book_appointment')
                except AppointmentSlot.DoesNotExist:
                    messages.error(request, "Invalid time slot.")
            else:
                messages.error(request, "Please select a time slot.")
        
        elif step == 4:
            # Step 4: Confirm and book
            slot_id = booking_data.get('slot_id')
            notes = request.POST.get('notes', '')
            
            if slot_id:
                try:
                    slot = AppointmentSlot.objects.get(id=slot_id)
                    doctor = DoctorProfile.objects.get(id=booking_data['doctor_id'])
                    
                    # Book appointment
                    appointment, success = AppointmentBookingService.book_appointment(
                        patient=patient,
                        doctor=doctor,
                        slot=slot,
                        notes_for_staff=notes
                    )
                    
                    if success:
                        # Clear booking data
                        if 'booking_data' in request.session:
                            del request.session['booking_data']
                        
                        messages.success(request, f"Appointment booked successfully! Code: {appointment.appointment_code}")
                        return redirect('appointments:appointment_detail', pk=appointment.pk)
                    else:
                        messages.error(request, "Failed to book appointment. Please try again.")
                        
                except AppointmentSlot.DoesNotExist:
                    messages.error(request, "Selected slot not available.")
                except Exception as e:
                    messages.error(request, f"Error: {str(e)}")
            else:
                messages.error(request, "No time slot selected.")
    
    # Determine current step
    current_step = 1
    if booking_data.get('doctor_id'):
        current_step = 2
    if booking_data.get('selected_date'):
        current_step = 3
    if booking_data.get('slot_id'):
        current_step = 4
    
    # Get data for current step
    context = {
        'steps': steps,
        'current_step': current_step,
        'user_role': _get_user_role(request.user)
    }
    
    # Step 1: Get doctors
    if current_step == 1:
        context['doctors'] = DoctorProfile.objects.filter(
            user__is_active=True
        ).select_related('user').order_by('user__first_name')
    
    # Step 2: Get available dates for selected doctor
    elif current_step == 2:
        doctor_id = booking_data.get('doctor_id')
        if doctor_id:
            # Get available slots for next 30 days
            available_dates = AppointmentSlot.objects.filter(
                doctor_id=doctor_id,
                status=AppointmentSlot.Status.AVAILABLE,
                start_datetime__gte=timezone.now(),
                start_datetime__lte=timezone.now() + timedelta(days=30)
            ).dates('start_datetime', 'day')
            
            context['available_dates'] = available_dates
            context['selected_doctor'] = DoctorProfile.objects.get(id=doctor_id)
    
    # Step 3: Get available time slots for selected date
    elif current_step == 3:
        doctor_id = booking_data.get('doctor_id')
        selected_date = booking_data.get('selected_date')
        
        if doctor_id and selected_date:
            available_slots = AppointmentSlot.objects.filter(
                doctor_id=doctor_id,
                status=AppointmentSlot.Status.AVAILABLE,
                start_datetime__date=selected_date
            ).order_by('start_datetime')
            
            context['available_slots'] = available_slots
            context['selected_doctor'] = DoctorProfile.objects.get(id=doctor_id)
            context['selected_date'] = selected_date
    
    # Step 4: Confirmation
    elif current_step == 4:
        doctor_id = booking_data.get('doctor_id')
        slot_id = booking_data.get('slot_id')
        
        if doctor_id and slot_id:
            context['selected_doctor'] = DoctorProfile.objects.get(id=doctor_id)
            context['selected_slot'] = AppointmentSlot.objects.get(id=slot_id)
    
    # Add selected data to context
    context.update({
        'selected_doctor_id': booking_data.get('doctor_id', ''),
        'selected_date': booking_data.get('selected_date', ''),
        'selected_slot_id': booking_data.get('slot_id', '')
    })
    
    return render(request, 'appointments/book.html', context)


# @login_required
def update_appointment_status(request, pk, action):
    """Update appointment status"""
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # For testing without auth, skip permission check
    # if not _can_update_status(request.user, appointment, action):
    #     messages.error(request, "You don't have permission to perform this action.")
    #     return redirect('appointments:appointment_detail', pk=appointment.pk)
    
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


# @login_required
def reschedule_appointment(request, pk):
    """Reschedule an appointment"""
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # For testing without auth, skip permission check
    # if not AppointmentRescheduleService.can_reschedule(appointment, request.user):
    #     messages.error(request, "You cannot reschedule this appointment.")
    #     return redirect('appointments:appointment_detail', pk=appointment.pk)
    
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
    
    return render(request, 'appointments/reschedule.html', context)


# @login_required
def search_appointments(request):
    """Search appointments (staff only)"""
    # For testing without auth, skip permission check
    # if not (hasattr(request.user, 'receptionist_profile') or hasattr(request.user, 'admin_profile')):
    #     messages.error(request, "Permission denied.")
    #     return redirect('appointments:appointment_list')
    
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
    
    return render(request, 'appointments/manage.html', context)


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
