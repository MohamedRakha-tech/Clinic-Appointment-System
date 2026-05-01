from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from datetime import timedelta

from accounts.mixins import DoctorRequiredMixin as AccountsDoctorRequiredMixin
from accounts.utils import get_user_role, user_has_role
from accounts.models import DoctorProfile
from scheduling.forms import DoctorScheduleExceptionForm, DoctorWeeklyScheduleForm
from scheduling.models import (
    AppointmentSlot,
    DoctorScheduleException,
    DoctorWeeklySchedule,
)
from scheduling.services import SlotGenerationService


def style_form_fields(form):
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")

        if getattr(field.widget, "input_type", None) == "checkbox":
            field.widget.attrs["class"] = "form-check-input"
        elif field.widget.__class__.__name__ == "Select":
            field.widget.attrs["class"] = "form-select"

    return form


def is_scheduling_manager(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False

    role = get_user_role(user)
    if role == "doctor":
        return False

    if user_has_role(user, ["admin", "receptionist"]):
        return True

    return user.is_staff


def is_doctor(user):
    return user.is_authenticated and hasattr(user, "doctor_profile")


class SchedulingManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return is_scheduling_manager(self.request.user)


class DoctorRequiredMixin(AccountsDoctorRequiredMixin):
    def get_doctor_profile(self):
        return self.request.user.doctor_profile


class SchedulingFormStyleMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        return style_form_fields(form)


class WeeklyScheduleListView(SchedulingManagerRequiredMixin, ListView):
    model = DoctorWeeklySchedule
    template_name = "scheduling/weekly_schedule_list.html"
    context_object_name = "schedules"
    paginate_by = 10

    def get_queryset(self):
        queryset = DoctorWeeklySchedule.objects.select_related("doctor", "doctor__user")

        doctor_id = self.request.GET.get("doctor")
        day_of_week = self.request.GET.get("day_of_week")
        status = self.request.GET.get("status")
        specialization = self.request.GET.get("specialization")
        search = self.request.GET.get("search")

        if doctor_id and is_scheduling_manager(self.request.user):
            queryset = queryset.filter(doctor_id=doctor_id)

        if day_of_week:
            queryset = queryset.filter(day_of_week=day_of_week)

        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        if specialization:
            queryset = queryset.filter(doctor__specialization=specialization)

        if search:
            queryset = queryset.filter(
                Q(doctor__user__first_name__icontains=search)
                | Q(doctor__user__last_name__icontains=search)
                | Q(doctor__specialization__icontains=search)
            )

        return queryset.order_by("doctor", "day_of_week", "start_time")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_scheduling"] = is_scheduling_manager(self.request.user)
        context["doctors"] = DoctorProfile.objects.select_related("user").order_by("user__username")
        context["day_choices"] = DoctorWeeklySchedule.DAY_CHOICES
        context["specializations"] = (
            DoctorProfile.objects.order_by("specialization")
            .values_list("specialization", flat=True)
            .distinct()
        )
        context["filters"] = {
            "doctor": self.request.GET.get("doctor", ""),
            "day_of_week": self.request.GET.get("day_of_week", ""),
            "status": self.request.GET.get("status", ""),
            "specialization": self.request.GET.get("specialization", ""),
        }
        filtered_queryset = self.get_queryset()
        pagination_query = self.request.GET.copy()
        pagination_query.pop("page", None)
        context["pagination_query"] = pagination_query.urlencode()
        context["page_range"] = context["paginator"].get_elided_page_range(
            number=context["page_obj"].number,
            on_each_side=1,
            on_ends=1,
        )
        context["total_schedules"] = filtered_queryset.count()
        context["active_schedules"] = filtered_queryset.filter(is_active=True).count()
        context["inactive_schedules"] = filtered_queryset.filter(is_active=False).count()
        capacity_minutes = 0
        for schedule in filtered_queryset:
            start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
            end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
            capacity_minutes += max(end_minutes - start_minutes, 0)
        context["total_weekly_capacity_hours"] = round(capacity_minutes / 60)
        context["practitioner_coverage"] = self._weekly_coverage()
        return context

    def _weekly_coverage(self):
        total_doctors = DoctorProfile.objects.count()
        if total_doctors == 0:
            return 0

        covered_doctors = DoctorWeeklySchedule.objects.filter(
            is_active=True
        ).values("doctor").distinct().count()
        return round((covered_doctors / total_doctors) * 100)


class WeeklyScheduleCreateView(SchedulingFormStyleMixin, SchedulingManagerRequiredMixin, CreateView):
    model = DoctorWeeklySchedule
    form_class = DoctorWeeklyScheduleForm
    template_name = "scheduling/weekly_schedule_form.html"
    success_url = reverse_lazy("scheduling:weekly_schedule_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_scheduling"] = True
        context["form_mode"] = "Add"
        context["recent_schedules"] = DoctorWeeklySchedule.objects.select_related(
            "doctor", "doctor__user"
        ).order_by("-updated_at")[:2]
        context["active_doctors_count"] = DoctorProfile.objects.count()
        context["weekly_coverage"] = self._weekly_coverage()
        return context

    def _weekly_coverage(self):
        total_doctors = DoctorProfile.objects.count()
        if total_doctors == 0:
            return 0

        covered_doctors = DoctorWeeklySchedule.objects.filter(
            is_active=True
        ).values("doctor").distinct().count()
        return round((covered_doctors / total_doctors) * 100)


class WeeklyScheduleUpdateView(SchedulingFormStyleMixin, SchedulingManagerRequiredMixin, UpdateView):
    model = DoctorWeeklySchedule
    form_class = DoctorWeeklyScheduleForm
    template_name = "scheduling/weekly_schedule_form.html"
    success_url = reverse_lazy("scheduling:weekly_schedule_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_scheduling"] = True
        context["form_mode"] = "Edit"
        return context

class ScheduleExceptionListView(SchedulingManagerRequiredMixin, ListView):
    model = DoctorScheduleException
    template_name = "scheduling/schedule_exception_list.html"
    context_object_name = "exceptions"

    def get_queryset(self):
        queryset = DoctorScheduleException.objects.select_related(
            "doctor",
            "doctor__user",
            "created_by",
        )

        doctor_id = self.request.GET.get("doctor")
        exception_date = self.request.GET.get("date")
        exception_type = self.request.GET.get("type")
        search = self.request.GET.get("search")

        if doctor_id and is_scheduling_manager(self.request.user):
            queryset = queryset.filter(doctor_id=doctor_id)

        if exception_date:
            queryset = queryset.filter(exception_date=exception_date)

        if exception_type:
            queryset = queryset.filter(type=exception_type)

        if search:
            queryset = queryset.filter(
                Q(doctor__user__first_name__icontains=search)
                | Q(doctor__user__last_name__icontains=search)
                | Q(doctor__specialization__icontains=search)
            )

        return queryset.order_by("-exception_date", "doctor")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_scheduling"] = is_scheduling_manager(self.request.user)
        context["doctors"] = DoctorProfile.objects.select_related("user").order_by("user__username")
        context["type_choices"] = DoctorScheduleException.ExceptionType.choices
        context["filters"] = {
            "doctor": self.request.GET.get("doctor", ""),
            "date": self.request.GET.get("date", ""),
            "type": self.request.GET.get("type", ""),
        }
        context["total_exceptions"] = DoctorScheduleException.objects.count()
        return context


class ScheduleExceptionCreateView(SchedulingFormStyleMixin, SchedulingManagerRequiredMixin, CreateView):
    model = DoctorScheduleException
    form_class = DoctorScheduleExceptionForm
    template_name = "scheduling/schedule_exception_form.html"
    success_url = reverse_lazy("scheduling:schedule_exception_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_scheduling"] = True
        context["form_mode"] = "Add"
        context["recent_exceptions"] = DoctorScheduleException.objects.select_related(
            "doctor", "doctor__user"
        ).order_by("-created_at")[:3]
        return context


class ScheduleExceptionUpdateView(SchedulingFormStyleMixin, SchedulingManagerRequiredMixin, UpdateView):
    model = DoctorScheduleException
    form_class = DoctorScheduleExceptionForm
    template_name = "scheduling/schedule_exception_form.html"
    success_url = reverse_lazy("scheduling:schedule_exception_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage_scheduling"] = True
        context["form_mode"] = "Edit"
        return context

class AppointmentSlotListView(SchedulingManagerRequiredMixin, ListView):
    model = AppointmentSlot
    template_name = "scheduling/appointment_slot_list.html"
    context_object_name = "slots"
    paginate_by = 10

    def get_queryset(self):
        queryset = AppointmentSlot.objects.select_related("doctor", "doctor__user")

        doctor_id = self.request.GET.get("doctor")
        slot_date = self.request.GET.get("date")
        status = self.request.GET.get("status")
        generated_from = self.request.GET.get("generated_from")
        search = self.request.GET.get("search")

        if doctor_id and is_scheduling_manager(self.request.user):
            queryset = queryset.filter(doctor_id=doctor_id)

        if slot_date:
            queryset = queryset.filter(slot_date=slot_date)

        if status:
            queryset = queryset.filter(status=status)

        if generated_from:
            queryset = queryset.filter(generated_from=generated_from)

        if search:
            queryset = queryset.filter(
                Q(doctor__user__first_name__icontains=search)
                | Q(doctor__user__last_name__icontains=search)
                | Q(doctor__specialization__icontains=search)
            )

        return queryset.order_by("slot_date", "start_datetime")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()

        doctors = DoctorProfile.objects.select_related("user").order_by("user__username")
        context["doctors"] = doctors
        context["status_choices"] = AppointmentSlot.Status.choices
        context["generated_from_choices"] = AppointmentSlot.GeneratedFrom.choices
        context["filters"] = {
            "doctor": self.request.GET.get("doctor", ""),
            "date": self.request.GET.get("date", ""),
            "status": self.request.GET.get("status", ""),
            "generated_from": self.request.GET.get("generated_from", ""),
        }
        pagination_query = self.request.GET.copy()
        pagination_query.pop("page", None)
        context["pagination_query"] = pagination_query.urlencode()
        context["page_range"] = context["paginator"].get_elided_page_range(
            number=context["page_obj"].number,
            on_each_side=1,
            on_ends=1,
        )
        context["can_manage_scheduling"] = is_scheduling_manager(self.request.user)
        context["total_slots"] = filtered_queryset.count()
        context["available_count"] = filtered_queryset.filter(
            status=AppointmentSlot.Status.AVAILABLE
        ).count()
        context["booked_count"] = filtered_queryset.filter(
            status=AppointmentSlot.Status.BOOKED
        ).count()
        context["blocked_count"] = filtered_queryset.filter(
            status=AppointmentSlot.Status.BLOCKED
        ).count()
        context["expired_count"] = filtered_queryset.filter(
            status=AppointmentSlot.Status.EXPIRED
        ).count()
        return context


class GenerateSlotsView(SchedulingManagerRequiredMixin, View):
    template_name = "scheduling/generate_slots.html"

    def get(self, request):
        return render(request, self.template_name, self.get_context())

    def post(self, request):
        context = self.get_context()
        start_date, end_date, error = self.get_date_range(request.POST)

        if error:
            context["form_error"] = error
            return render(request, self.template_name, context)

        service = SlotGenerationService()
        doctor_id = request.POST.get("doctor")

        if doctor_id:
            try:
                doctor = DoctorProfile.objects.get(pk=doctor_id)
            except DoctorProfile.DoesNotExist:
                context["form_error"] = "Selected doctor was not found."
                return render(request, self.template_name, context)

            summary = service.generate_slots_for_doctor(doctor, start_date, end_date)
        else:
            summary = service.generate_slots_for_all_doctors(start_date, end_date)

        context["summary"] = summary
        context["selected_doctor"] = doctor_id
        context["start_date"] = start_date
        context["end_date"] = end_date
        return render(request, self.template_name, context)

    def get_context(self):
        today = timezone.localdate()
        return {
            "can_manage_scheduling": True,
            "doctors": DoctorProfile.objects.select_related("user").order_by("user__username"),
            "summary": None,
            "start_date": today,
            "end_date": today + timedelta(days=30),
            "total_doctors": DoctorProfile.objects.count(),
            "total_slots": AppointmentSlot.objects.count(),
            "available_slots": AppointmentSlot.objects.filter(
                status=AppointmentSlot.Status.AVAILABLE
            ).count(),
            "blocked_slots": AppointmentSlot.objects.filter(
                status=AppointmentSlot.Status.BLOCKED
            ).count(),
        }

    def get_date_range(self, data):
        days = data.get("days")
        if days:
            try:
                days = int(days)
            except ValueError:
                return None, None, "Days must be a whole number."

            if days < 0:
                return None, None, "Days must be 0 or greater."

            start_date = timezone.localdate()
            end_date = start_date + timedelta(days=days)
            return start_date, end_date, None

        start_date = parse_date(data.get("start_date") or "")
        end_date = parse_date(data.get("end_date") or "")

        if not start_date or not end_date:
            return None, None, "Provide start and end dates, or a days value."

        if start_date > end_date:
            return None, None, "Start date must be before or equal to end date."

        return start_date, end_date, None

class DoctorMyScheduleView(DoctorRequiredMixin, View):
    template_name = "scheduling/doctor_my_schedule.html"

    def get_doctor_profile(self):
        if is_doctor(self.request.user):
            return self.request.user.doctor_profile
        return None

    def get(self, request):
        doctor = self.get_doctor_profile()
        if doctor is None:
            context = {
                "can_manage_scheduling": is_scheduling_manager(request.user),
                "doctor": None,
                "week_start": timezone.localdate(),
                "week_end": timezone.localdate() + timedelta(days=6),
                "schedule_days": [],
                "exceptions": [],
                "upcoming_slots": [],
                "available_slots_count": 0,
                "no_doctor_profile": True,
            }
            return render(request, self.template_name, context)

        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        week_dates = [week_start + timedelta(days=offset) for offset in range(7)]
        weekly_schedules = DoctorWeeklySchedule.objects.filter(
            doctor=doctor,
            is_active=True,
        ).order_by("day_of_week", "start_time")
        exceptions = DoctorScheduleException.objects.filter(
            doctor=doctor,
            exception_date__gte=week_start,
            exception_date__lte=week_start + timedelta(days=13),
        ).order_by("exception_date")
        slots = AppointmentSlot.objects.filter(
            doctor=doctor,
            slot_date__gte=today,
        ).order_by("slot_date", "start_datetime")

        schedule_days = []
        for current_date in week_dates:
            schedule_days.append({
                "date": current_date,
                "schedules": weekly_schedules.filter(day_of_week=current_date.weekday()),
                "slots": slots.filter(slot_date=current_date)[:4],
            })

        context = {
            "can_manage_scheduling": is_scheduling_manager(request.user),
            "doctor": doctor,
            "week_start": week_start,
            "week_end": week_start + timedelta(days=6),
            "schedule_days": schedule_days,
            "exceptions": exceptions,
            "upcoming_slots": slots[:8],
            "available_slots_count": slots.filter(status=AppointmentSlot.Status.AVAILABLE).count(),
        }
        return render(request, self.template_name, context)
