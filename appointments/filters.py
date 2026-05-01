from datetime import date as date_type

from django.db.models import Q
from django.utils import timezone

from accounts.models import DoctorProfile, PatientProfile
from appointments.models import Appointment
from scheduling.models import AppointmentSlot


def is_clinic_staff(user):
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    for attr in ("doctor_profile", "receptionist_profile", "admin_profile"):
        if hasattr(user, attr):
            return True

    return False


def can_manage_all_appointments(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if hasattr(user, "receptionist_profile") or hasattr(user, "admin_profile"):
        return True

    if user.is_staff and not hasattr(user, "doctor_profile"):
        return True

    return False


def appointments_for_user(user):
    queryset = (
        Appointment.objects.select_related(
            "patient",
            "patient__user",
            "doctor",
            "doctor__user",
            "slot",
        ).order_by("-scheduled_start", "-id")
    )

    if not user.is_authenticated:
        return queryset.none()

    if hasattr(user, "patient_profile"):
        return queryset.filter(patient=user.patient_profile)

    if hasattr(user, "doctor_profile") and not can_manage_all_appointments(user):
        return queryset.filter(doctor=user.doctor_profile)

    if can_manage_all_appointments(user):
        return queryset

    return queryset.none()


def patient_appointments_for_user(user):
    queryset = (
        Appointment.objects.select_related(
            "patient",
            "patient__user",
            "doctor",
            "doctor__user",
            "slot",
        ).order_by("-scheduled_start", "-id")
    )

    if not user.is_authenticated or not hasattr(user, "patient_profile"):
        return queryset.none()

    return queryset.filter(patient=user.patient_profile)


def appointment_detail_queryset_for_user(user):
    return appointments_for_user(user)


def appointment_history_queryset_for_user(user):
    return appointments_for_user(user)


def apply_appointment_list_filters(queryset, params, is_staff=False):
    status = (params.get("status") or "").strip()
    query = (params.get("q") or params.get("search") or "").strip()
    date_from = (params.get("date_from") or "").strip()
    date_to = (params.get("date_to") or "").strip()
    doctor_id = (params.get("doctor_id") or "").strip()
    patient_id = (params.get("patient_id") or "").strip()

    if status:
        queryset = queryset.filter(status=status)

    if doctor_id.isdigit():
        queryset = queryset.filter(doctor_id=doctor_id)

    if is_staff and patient_id.isdigit():
        queryset = queryset.filter(patient_id=patient_id)

    if query:
        search_filter = (
            Q(appointment_code__icontains=query)
            | Q(doctor__user__username__icontains=query)
            | Q(doctor__user__first_name__icontains=query)
            | Q(doctor__user__last_name__icontains=query)
            | Q(doctor__specialization__icontains=query)
        )
        if is_staff:
            search_filter |= (
                Q(patient__user__username__icontains=query)
                | Q(patient__user__first_name__icontains=query)
                | Q(patient__user__last_name__icontains=query)
            )
        queryset = queryset.filter(search_filter)

    if date_from:
        try:
            queryset = queryset.filter(scheduled_start__date__gte=date_type.fromisoformat(date_from))
        except ValueError:
            pass

    if date_to:
        try:
            queryset = queryset.filter(scheduled_start__date__lte=date_type.fromisoformat(date_to))
        except ValueError:
            pass

    return queryset


def available_doctors_for_booking():
    return DoctorProfile.objects.select_related("user").order_by("user__first_name", "user__last_name", "user__username")


def available_slots_for_doctor(doctor, target_date=None):
    queryset = (
        AppointmentSlot.objects.select_related("doctor", "doctor__user")
        .filter(doctor=doctor, status=AppointmentSlot.Status.AVAILABLE)
        .order_by("start_datetime")
    )

    if target_date:
        queryset = queryset.filter(slot_date=target_date)
    else:
        today = timezone.localdate()
        queryset = queryset.filter(slot_date__gte=today)

    # Additional filter: exclude slots that have already passed today
    current_time = timezone.now()
    queryset = queryset.filter(start_datetime__gt=current_time)

    return queryset


def available_slots_queryset(doctor_id=None, target_date=None):
    queryset = (
        AppointmentSlot.objects.select_related("doctor", "doctor__user")
        .filter(status=AppointmentSlot.Status.AVAILABLE)
        .order_by("start_datetime")
    )

    if doctor_id:
        queryset = queryset.filter(doctor_id=doctor_id)

    if target_date:
        queryset = queryset.filter(slot_date=target_date)
    else:
        queryset = queryset.filter(slot_date__gte=timezone.localdate())

    # Additional filter: exclude slots that have already passed today
    current_time = timezone.now()
    queryset = queryset.filter(start_datetime__gt=current_time)

    return queryset
