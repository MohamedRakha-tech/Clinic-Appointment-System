from rest_framework import pagination, permissions, viewsets
from rest_framework.decorators import action
from django.utils.dateparse import parse_date
from django.utils import timezone

from scheduling.api.serializers import AppointmentSlotSerializer
from scheduling.models import AppointmentSlot


class AppointmentSlotPagination(pagination.PageNumberPagination):
    page_size = 20


class AppointmentSlotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentSlotSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = AppointmentSlotPagination
    queryset = AppointmentSlot.objects.select_related(
        "doctor",
        "doctor__user",
    ).order_by("slot_date", "start_datetime")

    # TODO: replace IsAuthenticated with role-based permissions after accounts permissions are finalized.

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "available":
            queryset = queryset.filter(status=AppointmentSlot.Status.AVAILABLE)
            # Additional filter: exclude slots that have already passed today
            current_time = timezone.now()
            queryset = queryset.filter(start_datetime__gt=current_time)
            return self._apply_filters(queryset, include_status=False)
        return self._apply_filters(queryset)

    def _apply_filters(self, queryset, include_status=True):
        params = self.request.query_params

        doctor = params.get("doctor")
        if doctor and doctor.isdigit():
            queryset = queryset.filter(doctor_id=doctor)

        slot_date = params.get("slot_date")
        parsed_slot_date = parse_date(slot_date) if slot_date else None
        if parsed_slot_date:
            queryset = queryset.filter(slot_date=parsed_slot_date)

        if include_status:
            status = params.get("status")
            allowed_statuses = {choice for choice, _ in AppointmentSlot.Status.choices}
            if status in allowed_statuses:
                queryset = queryset.filter(status=status)

        generated_from = params.get("generated_from")
        allowed_sources = {choice for choice, _ in AppointmentSlot.GeneratedFrom.choices}
        if generated_from in allowed_sources:
            queryset = queryset.filter(generated_from=generated_from)

        return queryset

    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
