from datetime import timedelta
from django.db.models import Count, Q, Value
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate, TruncMonth
from django.utils import timezone
from appointments.models import Appointment
from accounts.models import PatientProfile, DoctorProfile, User
from datetime import timedelta
from django.db.models.functions import Concat
import re
from queueing.models import AppointmentCheckin


def get_today_appointments_count():
    return Appointment.objects.filter(scheduled_start__date=timezone.localdate()).count()


def get_appointments_by_status(date=None):
    qs = Appointment.objects.all()
    if date:
        qs = qs.filter(scheduled_start__date=date)

    result = qs.values('status').annotate(count=Count('id'))
    return {row['status']: row['count'] for row in result}


def get_appointments_last_n_days(n=30):
    since = timezone.localdate() - timedelta(days=n)
    rows = (
        Appointment.objects
        .filter(scheduled_start__date__gte=since)
        .annotate(date=TruncDate('scheduled_start'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    data_dict = {}
    for row in rows:
        if row['date']:
            data_dict[str(row['date'])[:10]] = row['count']
            
    results = []
    for i in range(n + 1):
        current_date = since + timedelta(days=i)
        results.append({
            'date': current_date,
            'count': data_dict.get(str(current_date), 0)
        })
    return results


def get_pending_appointments_count():
    return Appointment.objects.filter(status='REQUESTED').count()


def get_monthly_revenue(year=None, month=None):
    today = timezone.localdate()
    year = year or today.year
    month = month or today.month

    completed = (
        Appointment.objects
        .filter(
            status='COMPLETED',
            scheduled_start__year=year,
            scheduled_start__month=month,
        )
        .select_related('doctor')
    )

    total = sum(
        getattr(appt.doctor, 'consultation_fee', 0)
        for appt in completed
    )
    return total


def get_total_revenue():
    completed = (
        Appointment.objects
        .filter(status='COMPLETED')
        .select_related('doctor')
    )
    return sum(
        getattr(appt.doctor, 'consultation_fee', 0)
        for appt in completed
    )


def get_total_completed_count():
    return Appointment.objects.filter(status='COMPLETED').count()

def get_revenue_last_n_months(n=6):

    today = timezone.localdate()
    since = today.replace(day=1) - timedelta(days=n * 30)

    rows = (
        Appointment.objects
        .filter(status='COMPLETED', scheduled_start__date__gte=since)
        .annotate(month=TruncMonth('scheduled_start'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    results = []
    for row in rows:
        results.append({
            'month': row['month'],
            'count': row['count'],
            'revenue': row['count'] * 150.00
        })

    return results

def get_revenue_last_n_days(n=30):
    since = timezone.localdate() - timedelta(days=n)
    rows = (
        Appointment.objects
        .filter(status='COMPLETED', scheduled_start__date__gte=since)
        .annotate(date=TruncDate('scheduled_start'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    data_dict = {}
    for row in rows:
        if row['date']:
            data_dict[str(row['date'])[:10]] = row['count']
            
    results = []
    for i in range(n + 1):
        current_date = since + timedelta(days=i)
        count = data_dict.get(str(current_date), 0)
        results.append({
            'date': current_date,
            'count': count,
            'revenue': count * 150.00
        })
    return results


def get_top_doctors(limit=5):
    since = timezone.localdate() - timedelta(days=30)
    return (
        Appointment.objects
        .filter(scheduled_start__date__gte=since, status='COMPLETED')
        .values('doctor__user__first_name', 'doctor__user__last_name', 'doctor__id')
        .annotate(total=Count('id'))
        .order_by('-total')[:limit]
    )


def get_doctor_today_queue(doctor_user_id):
    return (
        Appointment.objects
        .filter(
            doctor__user_id=doctor_user_id,
            scheduled_start__date=timezone.localdate(),
            status=Appointment.Status.CHECKED_IN,
        )
        .select_related('patient__user')
        .order_by('scheduled_start')
    )


def get_doctor_today_schedule(doctor_user_id):
    return (
        Appointment.objects
        .filter(
            doctor__user_id=doctor_user_id,
            scheduled_start__date=timezone.localdate(),
            status__in=[
                Appointment.Status.CONFIRMED,
                Appointment.Status.CHECKED_IN,
                Appointment.Status.COMPLETED,
            ],
        )
        .select_related('patient__user')
        .order_by('scheduled_start')
    )


def get_doctor_today_queue_count(doctor_user_id):
    return AppointmentCheckin.objects.filter(
        appointment__doctor__user_id=doctor_user_id,
        appointment__scheduled_start__date=timezone.localdate(),
        appointment__status=Appointment.Status.CHECKED_IN,
    ).count()


def get_doctor_completed_today_count(doctor_user_id):
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__date=timezone.localdate(),
        status=Appointment.Status.COMPLETED,
    ).count()


def get_doctor_upcoming_today_count(doctor_user_id):
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__date=timezone.localdate(),
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN],
    ).count()


def get_doctor_requested_today_count(doctor_user_id):
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__date=timezone.localdate(),
        status=Appointment.Status.REQUESTED,
    ).count()


def get_doctor_confirmed_today_count(doctor_user_id):
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__date=timezone.localdate(),
        status=Appointment.Status.CONFIRMED,
    ).count()


def get_doctor_today_status_summary(doctor_user_id):
    today = timezone.localdate()
    appointments = Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__date=today,
    )
    requested_count = appointments.filter(status=Appointment.Status.REQUESTED).count()
    confirmed_count = appointments.filter(status=Appointment.Status.CONFIRMED).count()
    checked_in_count = appointments.filter(status=Appointment.Status.CHECKED_IN).count()
    completed_count = appointments.filter(status=Appointment.Status.COMPLETED).count()

    if checked_in_count:
        tone = "action"
        title = f"{checked_in_count} patient{'s' if checked_in_count != 1 else ''} waiting"
        message = "Your queue has checked-in patients ready for consultation."
    elif confirmed_count:
        tone = "watch"
        title = f"{confirmed_count} confirmed appointment{'s' if confirmed_count != 1 else ''} today"
        if requested_count:
            message = (
                f"{requested_count} more request{'s' if requested_count != 1 else ''} "
                "are still waiting for front-desk confirmation."
            )
        else:
            message = "No one is waiting yet, but your confirmed schedule is active."
    elif requested_count:
        tone = "watch"
        title = f"{requested_count} requested appointment{'s' if requested_count != 1 else ''}"
        message = "These visits are not confirmed yet, so they should not enter your live queue."
    elif completed_count:
        tone = "calm"
        title = "Today's queue is clear"
        message = "All checked-in visits have been handled for now."
    else:
        tone = "calm"
        title = "No active queue today"
        message = "You do not have any active patient flow at the moment."

    return {
        "requested_count": requested_count,
        "confirmed_count": confirmed_count,
        "checked_in_count": checked_in_count,
        "completed_count": completed_count,
        "tone": tone,
        "title": title,
        "message": message,
    }


def get_today_appointments_list():
    return (
        Appointment.objects
        .filter(scheduled_start__date=timezone.localdate())
        .select_related('patient__user', 'doctor__user')
        .order_by('scheduled_start')
    )


def get_total_patients_count():
    return PatientProfile.objects.filter(user__is_active=True).count()


def get_new_patients_this_month():
    today = timezone.localdate()
    return PatientProfile.objects.filter(
        user__date_joined__year=today.year,
        user__date_joined__month=today.month,
        user__is_active=True,
    ).count()


def get_peak_hours(days_back=30):

    since = timezone.localdate() - timedelta(days=days_back)

    return (
        Appointment.objects
        .filter(scheduled_start__date__gte=since)
        .exclude(status='CANCELLED')
        .annotate(hour=ExtractHour('scheduled_start'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('-count')
    )


def get_busiest_days(days_back=30):

    since = timezone.localdate() - timedelta(days=days_back)

    return (
        Appointment.objects
        .filter(scheduled_start__date__gte=since)
        .exclude(status='CANCELLED')
        .annotate(weekday=ExtractWeekDay('scheduled_start'))
        .values('weekday')
        .annotate(count=Count('id'))
        .order_by('-count')
    )


def get_noshow_rate(days_back=30):
    since = timezone.localdate() - timedelta(days=days_back)
    qs = Appointment.objects.filter(scheduled_start__date__gte=since)
    total = qs.exclude(status='CANCELLED').count()
    noshows = qs.filter(status='NO_SHOW').count()
    rate = round((noshows / total * 100), 1) if total > 0 else 0.0
    return {
        'total':   total,
        'noshows': noshows,
        'rate':    rate,
    }


def get_noshow_rate_per_doctor(days_back=30):
    since = timezone.localdate() - timedelta(days=days_back)
    doctors = (
        Appointment.objects
        .filter(scheduled_start__date__gte=since)
        .exclude(status='CANCELLED')
        .values('doctor__user__id', 'doctor__user__first_name', 'doctor__user__last_name')
        .annotate(
            total=Count('id'),
            noshows=Count('id', filter=Q(status='NO_SHOW')),
        )
        .order_by('-noshows')
    )

    result = []
    for row in doctors:
        total = row['total']
        noshows = row['noshows']
        result.append({
            'doctor_id':   row['doctor__user__id'],
            'doctor_name': f"{row['doctor__user__first_name']} {row['doctor__user__last_name']}",
            'total':       total,
            'noshows':     noshows,
            'rate':        round((noshows / total * 100), 1) if total > 0 else 0.0,
        })

    return result



def get_filtered_appointments(
    status=None,
    date_from=None,
    date_to=None,
    doctor_id=None,
    search=None,
):

    qs = (
        Appointment.objects
        .select_related('patient__user', 'doctor__user')
        .order_by('-scheduled_start')
    )

    if status:
        qs = qs.filter(status=status)

    if date_from:
        qs = qs.filter(scheduled_start__date__gte=date_from)

    if date_to:
        qs = qs.filter(scheduled_start__date__lte=date_to)

    if doctor_id:
        qs = qs.filter(doctor__user__id=doctor_id)

    if search:
        search = search.strip()
        search = re.sub(r'\s+', ' ', search)
        qs = qs.annotate(
            full_name=Concat('patient__user__first_name', Value(' '), 'patient__user__last_name')
        ).filter(
            Q(appointment_code__icontains=search) |
            Q(full_name__icontains=search) |
            Q(patient__user__first_name__icontains=search) |
            Q(patient__user__last_name__icontains=search)
        )

    return qs


def get_all_doctors():
    return DoctorProfile.objects.select_related('user').all()

def get_total_doctors_count():
    return DoctorProfile.objects.filter(user__is_active=True).count()

def get_all_staff_users():
    return User.objects.filter(patient_profile__isnull=True).order_by('first_name')


def get_appointments_all_dates(years_back=3):
    today = timezone.localdate()
    since = today - timedelta(days=years_back * 365)
    rows = (
        Appointment.objects
        .filter(scheduled_start__date__gte=since)
        .annotate(date=TruncDate('scheduled_start'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    data_dict = {}
    for row in rows:
        if row['date']:
            data_dict[str(row['date'])[:10]] = row['count']
            
    results = []
    current_date = since
    while current_date <= today:
        results.append({
            'date': current_date,
            'count': data_dict.get(str(current_date), 0)
        })
        current_date += timedelta(days=1)
    return results

def get_revenue_all_dates(years_back=3):
    today = timezone.localdate()
    since = today - timedelta(days=years_back * 365)
    rows = (
        Appointment.objects
        .filter(status='COMPLETED', scheduled_start__date__gte=since)
        .annotate(date=TruncDate('scheduled_start'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    data_dict = {}
    for row in rows:
        if row['date']:
            data_dict[str(row['date'])[:10]] = row['count']
            
    results = []
    current_date = since
    while current_date <= today:
        count = data_dict.get(str(current_date), 0)
        results.append({
            'date': current_date,
            'count': count,
            'revenue': count * 150.00
        })
        current_date += timedelta(days=1)
    return results


def get_revenue_all_months(years_back=3):
    since = timezone.localdate().replace(day=1) - timedelta(days=years_back * 365)
    rows = (
        Appointment.objects
        .filter(status='COMPLETED', scheduled_start__date__gte=since)
        .annotate(month=TruncMonth('scheduled_start'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    results = []
    for row in rows:
        results.append({
            'date': row['month'],
            'count': row['count'],
            'revenue': row['count'] * 150.00
        })
    return results
