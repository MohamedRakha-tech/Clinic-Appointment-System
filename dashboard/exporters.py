import csv
from django.http import HttpResponse
from django.utils import timezone
from appointments.models import Appointment

from . import selectors


def _make_csv_response(filename):

    today = timezone.localdate().strftime('%Y-%m-%d')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="{filename}_{today}.csv"'
    )
    return response


def export_appointments_csv(qs=None, filters=None):
    if qs is None:
        qs = Appointment.objects.select_related(
            'patient__user', 'doctor__user'
        ).order_by('-scheduled_start')
        if filters:
            qs = qs.filter(**filters)

    response = _make_csv_response('appointments')
    writer   = csv.writer(response)

    writer.writerow([
        'ID', 'Patient Name', 'Patient Email',
        'Doctor Name', 'Date', 'Start Time', 'Status', 'Booked At',
    ])

    for appt in qs:
        patient_name = f"{appt.patient.user.first_name or ''} {appt.patient.user.last_name or ''}".strip() or appt.patient.user.username
        doctor_name  = f"{appt.doctor.user.first_name or ''} {appt.doctor.user.last_name or ''}".strip() or appt.doctor.user.username
        writer.writerow([
            appt.id,
            patient_name,
            appt.patient.user.email,
            doctor_name,
            appt.scheduled_start.date(),
            appt.scheduled_start.strftime('%H:%M'),
            appt.status,
            appt.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response



def export_noshow_report_csv(days_back=30):
    data     = selectors.get_noshow_rate_per_doctor(days_back=days_back)
    response = _make_csv_response('noshow_report')
    writer   = csv.writer(response)

    writer.writerow([
        'Doctor Name',
        'Total Appointments',
        'No-Shows',
        'No-Show Rate (%)',
    ])

    for row in data:
        writer.writerow([
            row['doctor_name'],
            row['total'],
            row['noshows'],
            row['rate'],
        ])

    return response



def export_revenue_report_csv(months=6):
    data     = selectors.get_revenue_last_n_months(months)
    response = _make_csv_response('revenue_report')
    writer   = csv.writer(response)

    writer.writerow(['Month', 'Appointments Count'])

    for row in data:
        writer.writerow([
            row['month'].strftime('%Y-%m'),
            row['count'],
        ])

    return response


def export_users_csv():
    from accounts.utils import get_user_role
    from accounts.models import User
    
    response = _make_csv_response('clinic_users')
    writer = csv.writer(response)
    writer.writerow(["Username", "Email", "Role", "Active", "Created"])
    
    for user in User.objects.all().order_by("username"):
        writer.writerow([
            user.username,
            user.email,
            get_user_role(user) or "unknown",
            "Yes" if user.is_active else "No",
            user.date_joined.strftime("%Y-%m-%d"),
        ])
    
    return response