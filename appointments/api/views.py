from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import PatientProfile
from appointments.filters import apply_appointment_list_filters, appointments_for_user, can_manage_all_appointments
from appointments.models import Appointment
from appointments.api.serializers import (
    AppointmentActionSerializer,
    AppointmentCreateSerializer,
    AppointmentRescheduleHistorySerializer,
    AppointmentSerializer,
    AppointmentStatusHistorySerializer,
)
from appointments.services import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    transition_appointment,
)


def _is_clinic_staff(user):
    return can_manage_all_appointments(user)


def _staff_denied_response():
    return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = (
        Appointment.objects.select_related(
            "patient",
            "patient__user",
            "doctor",
            "doctor__user",
            "slot",
        )
        .select_related("consultation_record")
        .prefetch_related("status_history", "reschedule_history")
        .order_by("-scheduled_start", "-id")
    )

    def get_queryset(self):
        queryset = appointments_for_user(self.request.user).select_related("consultation_record")
        is_staff = _is_clinic_staff(self.request.user)
        return apply_appointment_list_filters(queryset, self.request.query_params, is_staff=is_staff)

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentCreateSerializer
        if self.action in {"cancel", "reschedule", "confirm", "decline", "no_show", "check_in", "complete"}:
            return AppointmentActionSerializer
        return AppointmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            slot_id = serializer.validated_data["slot_id"]
            notes_for_staff = serializer.validated_data.get("notes_for_staff") or ""
            patient = self._resolve_patient_for_booking(serializer.validated_data)

            appointment = book_appointment(
                patient=patient,
                slot_id=slot_id,
                booked_by=request.user,
                notes_for_staff=notes_for_staff,
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        output = AppointmentSerializer(appointment, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def _resolve_patient_for_booking(self, validated_data):
        user = self.request.user
        if hasattr(user, "patient_profile"):
            return user.patient_profile

        patient_id = validated_data.get("patient_id")
        if not patient_id:
            raise serializers.ValidationError({"patient_id": "patient_id is required for staff bookings."})

        return get_object_or_404(PatientProfile, pk=patient_id)

    def _get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def retrieve(self, request, *args, **kwargs):
        instance = self._get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appointment = self._get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cancel_appointment(
                appointment,
                cancelled_by=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        if not _is_clinic_staff(request.user):
            return _staff_denied_response()
        appointment = self._get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            transition_appointment(
                appointment,
                Appointment.Status.CANCELLED,
                changed_by=request.user,
                reason=serializer.validated_data.get("reason") or "Declined by staff",
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        if not _is_clinic_staff(request.user):
            return _staff_denied_response()
        appointment = self._get_object()
        try:
            transition_appointment(
                appointment,
                Appointment.Status.CONFIRMED,
                changed_by=request.user,
                reason="Confirmed by staff",
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def no_show(self, request, pk=None):
        if not _is_clinic_staff(request.user):
            return _staff_denied_response()
        appointment = self._get_object()
        try:
            transition_appointment(
                appointment,
                Appointment.Status.NO_SHOW,
                changed_by=request.user,
                reason="Marked as no-show",
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def check_in(self, request, pk=None):
        if not _is_clinic_staff(request.user):
            return _staff_denied_response()
        appointment = self._get_object()
        try:
            transition_appointment(
                appointment,
                Appointment.Status.CHECKED_IN,
                changed_by=request.user,
                reason="Checked in",
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        if not _is_clinic_staff(request.user):
            return _staff_denied_response()
        appointment = self._get_object()
        try:
            transition_appointment(
                appointment,
                Appointment.Status.COMPLETED,
                changed_by=request.user,
                reason="Completed by clinician",
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        appointment = self._get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data.get("slot_id")
        if not slot_id:
            return Response({"detail": "slot_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reschedule_appointment(
                appointment,
                new_slot_id=slot_id,
                changed_by=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            return Response({"detail": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        appointment = self._get_object()
        status_history = appointment.status_history.select_related("changed_by").order_by("-created_at", "-id")
        reschedule_history = appointment.reschedule_history.select_related("changed_by").order_by("-created_at", "-id")

        return Response({
            "appointment": appointment.id,
            "appointment_code": appointment.appointment_code,
            "status_history": AppointmentStatusHistorySerializer(status_history, many=True).data,
            "reschedule_history": AppointmentRescheduleHistorySerializer(reschedule_history, many=True).data,
        })
