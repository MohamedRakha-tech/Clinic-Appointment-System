from datetime import date as date_type

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from accounts.mixins import (
    AppointmentQuerysetMixin,
    ClinicStaffRequiredMixin,
    PatientProfileRequiredMixin,
    StaffAppointmentRequiredMixin,
)
from appointments.filters import (
    can_manage_all_appointments,
    appointment_detail_queryset_for_user,
    appointment_history_queryset_for_user,
    apply_appointment_list_filters,
    available_doctors_for_booking,
    available_slots_for_doctor,
)
from appointments.forms import AppointmentActionForm, AppointmentBookingForm, AppointmentRescheduleForm
from appointments.models import Appointment
from appointments.services import book_appointment, cancel_appointment, reschedule_appointment, transition_appointment
from queueing.services import QueueService
from scheduling.models import AppointmentSlot


class AppointmentListView(LoginRequiredMixin, AppointmentQuerysetMixin, ListView):
    template_name = "appointments/list.html"
    context_object_name = "appointments"
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = apply_appointment_list_filters(queryset, self.request.GET, is_staff=self.context_is_staff())
        return queryset

    def context_is_staff(self):
        return can_manage_all_appointments(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = (self.request.GET.get("status") or "").strip()
        context["search_query"] = (self.request.GET.get("q") or "").strip()
        context["date_from"] = (self.request.GET.get("date_from") or "").strip()
        context["date_to"] = (self.request.GET.get("date_to") or "").strip()
        context["doctor_id"] = (self.request.GET.get("doctor_id") or "").strip()
        context["show_staff_actions"] = self.context_is_staff()
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["pagination_query"] = query_params.urlencode()
        return context


class AppointmentDetailView(LoginRequiredMixin, AppointmentQuerysetMixin, DetailView):
    template_name = "appointments/detail.html"
    context_object_name = "appointment"

    def get_queryset(self):
        return appointment_detail_queryset_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_history"] = self.object.status_history.select_related("changed_by").order_by("-created_at")
        context["reschedule_history"] = self.object.reschedule_history.select_related("changed_by").order_by("-created_at")
        user = self.request.user
        is_staff_user = user.is_authenticated and (
            user.is_staff
            or user.is_superuser
            or hasattr(user, "doctor_profile")
            or hasattr(user, "receptionist_profile")
            or hasattr(user, "admin_profile")
        )
        status = self.object.status

        context["can_manage"] = is_staff_user
        context["can_reschedule"] = status not in {
            Appointment.Status.CANCELLED,
            Appointment.Status.COMPLETED,
        }
        context["can_cancel"] = status not in {
            Appointment.Status.CANCELLED,
            Appointment.Status.COMPLETED,
        } and (is_staff_user or status == Appointment.Status.REQUESTED)

        # Status transition permissions (staff only)
        context["can_confirm"] = is_staff_user and status == Appointment.Status.REQUESTED
        context["can_check_in"] = is_staff_user and status == Appointment.Status.CONFIRMED
        context["can_mark_no_show"] = is_staff_user and status == Appointment.Status.REQUESTED

        # Patient can only cancel their own requested appointments
        context["is_patient"] = user.is_authenticated and hasattr(user, "patient_profile")

        return context


class AppointmentBookView(PatientProfileRequiredMixin, FormView):
    template_name = "appointments/book.html"
    form_class = AppointmentBookingForm

    def get_initial(self):
        initial = super().get_initial()
        doctor_id = self.request.GET.get("doctor_id")
        slot_id = self.request.GET.get("slot_id")
        if doctor_id and doctor_id.isdigit():
            initial["doctor_id"] = int(doctor_id)
        if slot_id and slot_id.isdigit():
            initial["slot_id"] = int(slot_id)
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("initial", self.get_initial())
        return kwargs

    def get_selected_doctor(self):
        doctor_id = self.request.GET.get("doctor_id") or self.request.POST.get("doctor_id")
        if doctor_id and doctor_id.isdigit():
            return available_doctors_for_booking().filter(pk=int(doctor_id)).first()
        return available_doctors_for_booking().first()

    def get_selected_date(self):
        selected = self.request.GET.get("date") or self.request.POST.get("date")
        if not selected:
            return timezone.localdate()
        try:
            parsed_date = date_type.fromisoformat(selected)
            # Validate that selected date is not in the past
            today = timezone.localdate()
            if parsed_date < today:
                messages.error(self.request, f"Cannot select past date {selected}. Please choose today or a future date.")
                return today
            return parsed_date
        except ValueError:
            messages.error(self.request, f"Invalid date format {selected}. Using today's date.")
            return timezone.localdate()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["doctors"] = available_doctors_for_booking()
        context["selected_doctor"] = self.get_selected_doctor()
        context["selected_date"] = self.get_selected_date()
        context["slot_api_url"] = reverse("scheduling_api:slot-available")
        context["patient"] = self.get_profile()
        return context

    def form_valid(self, form):
        patient = self.get_profile()
        try:
            appointment = book_appointment(
                patient=patient,
                slot_id=form.cleaned_data["slot_id"],
                booked_by=self.request.user,
                notes_for_staff=form.cleaned_data.get("notes_for_staff", ""),
            )
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, "Appointment booked successfully.")
        return redirect("appointment-detail", pk=appointment.pk)


class AppointmentCancelView(LoginRequiredMixin, AppointmentQuerysetMixin, FormView):
    template_name = "appointments/cancel_confirm.html"
    form_class = AppointmentActionForm

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["appointment"] = self.get_object()
        return context

    def form_valid(self, form):
        appointment = self.get_object()
        try:
            cancel_appointment(
                appointment,
                cancelled_by=self.request.user,
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, "Appointment cancelled.")
        return redirect("appointment-detail", pk=appointment.pk)


class AppointmentRescheduleView(LoginRequiredMixin, AppointmentQuerysetMixin, FormView):
    template_name = "appointments/reschedule.html"
    form_class = AppointmentRescheduleForm

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def get_selected_date(self):
        raw_date = self.request.GET.get("date")
        if not raw_date:
            appointment_date = timezone.localtime(self.get_object().scheduled_start).date()
            return max(appointment_date, timezone.localdate())
        try:
            parsed_date = date_type.fromisoformat(raw_date)
            # Validate that selected date is not in the past
            today = timezone.localdate()
            if parsed_date < today:
                messages.error(self.request, f"Cannot select past date {raw_date}. Please choose today or a future date.")
                return today
            return parsed_date
        except ValueError:
            messages.error(self.request, f"Invalid date format {raw_date}. Using today's date.")
            return timezone.localdate()

    def get_available_slots(self):
        appointment = self.get_object()
        return available_slots_for_doctor(appointment.doctor, self.get_selected_date())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.get_object()
        context["appointment"] = appointment
        context["available_slots"] = self.get_available_slots()
        context["selected_date"] = self.get_selected_date()
        context["slot_api_url"] = reverse("scheduling_api:slot-available")
        context["min_date"] = timezone.localdate()
        return context

    def form_valid(self, form):
        appointment = self.get_object()
        slot_id = self.request.POST.get("slot_id") or self.request.POST.get("new_slot_id")
        if not slot_id or not slot_id.isdigit():
            form.add_error(None, "Please choose a new slot.")
            return self.form_invalid(form)

        try:
            reschedule_appointment(
                appointment,
                new_slot_id=int(slot_id),
                changed_by=self.request.user,
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, "Appointment rescheduled.")
        return redirect("appointment-detail", pk=appointment.pk)


class AppointmentConfirmView(ClinicStaffRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment.objects.select_related("slot"), pk=pk)
        try:
            transition_appointment(
                appointment,
                Appointment.Status.CONFIRMED,
                changed_by=request.user,
                reason="Confirmed by staff",
            )
        except ValidationError as exc:
            messages.error(request, str(exc))
            return redirect("appointment-detail", pk=pk)

        messages.success(request, "Appointment confirmed.")
        return redirect("appointment-detail", pk=pk)


class AppointmentNoShowView(ClinicStaffRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment.objects.select_related("slot"), pk=pk)
        try:
            transition_appointment(
                appointment,
                Appointment.Status.NO_SHOW,
                changed_by=request.user,
                reason="Marked as no-show",
            )
        except ValidationError as exc:
            messages.error(request, str(exc))
            return redirect("appointment-detail", pk=pk)

        messages.success(request, "Appointment marked as no-show.")
        return redirect("appointment-detail", pk=pk)




class AppointmentDeclineView(ClinicStaffRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment.objects.select_related("slot"), pk=pk)
        try:
            transition_appointment(
                appointment,
                Appointment.Status.CANCELLED,
                changed_by=request.user,
                reason="Declined by staff",
            )
        except ValidationError as exc:
            messages.error(request, str(exc))
            return redirect("appointment-detail", pk=pk)

        messages.success(request, "Appointment declined.")
        return redirect("appointment-detail", pk=pk)


class AppointmentCheckInView(ClinicStaffRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment.objects.select_related("slot"), pk=pk)
        try:
            QueueService.check_in_patient(appointment.id, request.user)
        except ValidationError as exc:
            messages.error(request, str(exc))
            return redirect("appointment-detail", pk=pk)

        messages.success(request, "Appointment checked in.")
        return redirect("appointment-detail", pk=pk)




class AppointmentHistoryView(LoginRequiredMixin, AppointmentQuerysetMixin, DetailView):
    template_name = "appointments/history.html"
    context_object_name = "appointment"

    def get_queryset(self):
        return appointment_history_queryset_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_history"] = self.object.status_history.select_related("changed_by").order_by("-created_at")
        context["reschedule_history"] = self.object.reschedule_history.select_related("changed_by").order_by("-created_at")
        return context
