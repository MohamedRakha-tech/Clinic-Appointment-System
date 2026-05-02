from collections import defaultdict
from datetime import timedelta, datetime, time
from decimal import Decimal

from django.db.models import Count, Q, Value
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate, TruncMonth
from django.utils import timezone
from appointments.models import Appointment
from accounts.models import PatientProfile, DoctorProfile, User
from django.db.models.functions import Concat
import re
from queueing.models import AppointmentCheckin


def _appointment_fee(appointment):
    return appointment.doctor.consultation_fee or Decimal("0.00")


def _completed_appointments_with_fees(**filters):
    return (
        Appointment.objects
        .filter(status=Appointment.Status.COMPLETED, **filters)
        .select_related("doctor")
    )


def _revenue_points_for_dates(start_date, end_date):
    start_since, _ = get_day_bounds(start_date)
    _, end_until = get_day_bounds(end_date)
    rows = _completed_appointments_with_fees(
        scheduled_start__gte=start_since,
        scheduled_start__lte=end_until,
    )

    revenue_by_date = defaultdict(Decimal)
    count_by_date = defaultdict(int)
    for appt in rows:
        date_key = timezone.localtime(appt.scheduled_start).date().isoformat()
        revenue_by_date[date_key] += _appointment_fee(appt)
        count_by_date[date_key] += 1

    results = []
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.isoformat()
        results.append({
            'date': current_date,
            'count': count_by_date.get(date_key, 0),
            'revenue': float(revenue_by_date.get(date_key, Decimal("0.00"))),
        })
        current_date += timedelta(days=1)
    return results


def get_day_bounds(date_obj):
    start = timezone.make_aware(datetime.combine(date_obj, time.min))
    end = timezone.make_aware(datetime.combine(date_obj, time.max))
    return start, end

def get_month_bounds(year, month):
    start = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(microseconds=1)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1)) - timedelta(microseconds=1)
    return start, end


def get_today_appointments_count():
    start, end = get_day_bounds(timezone.localdate())
    return Appointment.objects.filter(scheduled_start__gte=start, scheduled_start__lte=end).count()


def get_appointments_by_status(date=None):
    qs = Appointment.objects.all()
    if date:
        start, end = get_day_bounds(date)
        qs = qs.filter(scheduled_start__gte=start, scheduled_start__lte=end)

    result = qs.values('status').annotate(count=Count('id'))
    return {row['status']: row['count'] for row in result}


def get_appointments_last_n_days(n=30):
    since_date = timezone.localdate() - timedelta(days=n)
    start_since, _ = get_day_bounds(since_date)
    
    rows = (
        Appointment.objects
        .filter(scheduled_start__gte=start_since)
        .values_list('scheduled_start', flat=True)
    )
    
    data_dict = {}
    for dt in rows:
        local_dt = timezone.localtime(dt)
        date_str = local_dt.date().isoformat()
        data_dict[date_str] = data_dict.get(date_str, 0) + 1
            
    results = []
    for i in range(n + 1):
        current_date = since_date + timedelta(days=i)
        results.append({
            'date': current_date,
            'count': data_dict.get(current_date.isoformat(), 0)
        })
    return results


def get_pending_appointments_count():
    return Appointment.objects.filter(status='REQUESTED').count()


def get_monthly_revenue(year=None, month=None):
    today = timezone.localdate()
    year = year or today.year
    month = month or today.month

    start, end = get_month_bounds(year, month)

    return sum(
        _appointment_fee(appt)
        for appt in _completed_appointments_with_fees(
            scheduled_start__gte=start,
            scheduled_start__lte=end,
        )
    )


def get_total_revenue():
    return sum(
        _appointment_fee(appt)
        for appt in _completed_appointments_with_fees()
    )


def get_total_completed_count():
    return Appointment.objects.filter(status='COMPLETED').count()

def get_revenue_last_n_months(n=6):

    today = timezone.localdate()
    since = today.replace(day=1) - timedelta(days=n * 30)
    since_dt = timezone.make_aware(datetime.combine(since.replace(day=1), time.min))

    rows = _completed_appointments_with_fees(scheduled_start__gte=since_dt)

    count_by_month = defaultdict(int)
    revenue_by_month = defaultdict(Decimal)
    for appt in rows:
        month_str = timezone.localtime(appt.scheduled_start).date().replace(day=1).isoformat()
        count_by_month[month_str] += 1
        revenue_by_month[month_str] += _appointment_fee(appt)

    results = []
    current = today.replace(day=1)
    months = []
    for _ in range(n + 1):
        months.insert(0, current)
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12)
        else:
            current = current.replace(month=current.month - 1)
            
    for m in months:
        month_key = m.isoformat()
        results.append({
            'month': m,
            'count': count_by_month.get(month_key, 0),
            'revenue': float(revenue_by_month.get(month_key, Decimal("0.00"))),
        })

    return results

def get_revenue_last_n_days(n=30):
    since_date = timezone.localdate() - timedelta(days=n)
    return _revenue_points_for_dates(since_date, timezone.localdate())


def get_top_doctors(limit=5):
    since_date = timezone.localdate() - timedelta(days=30)
    start_since, _ = get_day_bounds(since_date)
    return (
        Appointment.objects
        .filter(scheduled_start__gte=start_since, status='COMPLETED')
        .values('doctor__user__first_name', 'doctor__user__last_name', 'doctor__id')
        .annotate(total=Count('id'))
        .order_by('-total')[:limit]
    )


def get_doctor_today_queue(doctor_user_id):
    start, end = get_day_bounds(timezone.localdate())
    return (
        Appointment.objects
        .filter(
            doctor__user_id=doctor_user_id,
            scheduled_start__gte=start,
            scheduled_start__lte=end,
            status=Appointment.Status.CHECKED_IN,
        )
        .select_related('patient__user')
        .order_by('scheduled_start')
    )


def get_doctor_today_schedule(doctor_user_id):
    start, end = get_day_bounds(timezone.localdate())
    return (
        Appointment.objects
        .filter(
            doctor__user_id=doctor_user_id,
            scheduled_start__gte=start,
            scheduled_start__lte=end,
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
    start, end = get_day_bounds(timezone.localdate())
    return AppointmentCheckin.objects.filter(
        appointment__doctor__user_id=doctor_user_id,
        appointment__scheduled_start__gte=start,
        appointment__scheduled_start__lte=end,
        appointment__status=Appointment.Status.CHECKED_IN,
    ).count()


def get_doctor_completed_today_count(doctor_user_id):
    start, end = get_day_bounds(timezone.localdate())
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__gte=start,
        scheduled_start__lte=end,
        status=Appointment.Status.COMPLETED,
    ).count()


def get_doctor_upcoming_today_count(doctor_user_id):
    start, end = get_day_bounds(timezone.localdate())
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__gte=start,
        scheduled_start__lte=end,
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN],
    ).count()


def get_doctor_requested_today_count(doctor_user_id):
    start, end = get_day_bounds(timezone.localdate())
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__gte=start,
        scheduled_start__lte=end,
        status=Appointment.Status.REQUESTED,
    ).count()


def get_doctor_confirmed_today_count(doctor_user_id):
    start, end = get_day_bounds(timezone.localdate())
    return Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__gte=start,
        scheduled_start__lte=end,
        status=Appointment.Status.CONFIRMED,
    ).count()


def get_doctor_today_status_summary(doctor_user_id):
    start, end = get_day_bounds(timezone.localdate())
    appointments = Appointment.objects.filter(
        doctor__user_id=doctor_user_id,
        scheduled_start__gte=start,
        scheduled_start__lte=end,
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
    start, end = get_day_bounds(timezone.localdate())
    return (
        Appointment.objects
        .filter(scheduled_start__gte=start, scheduled_start__lte=end)
        .select_related('patient__user', 'doctor__user')
        .order_by('scheduled_start')
    )


def get_total_patients_count():
    return PatientProfile.objects.filter(user__is_active=True).count()


def get_new_patients_this_month():
    today = timezone.localdate()
    start, end = get_month_bounds(today.year, today.month)
    return PatientProfile.objects.filter(
        user__date_joined__gte=start,
        user__date_joined__lte=end,
        user__is_active=True,
    ).count()


def get_peak_hours(days_back=30):
    since_date = timezone.localdate() - timedelta(days=days_back)
    start_since, _ = get_day_bounds(since_date)
    
    rows = (
        Appointment.objects
        .filter(scheduled_start__gte=start_since)
        .exclude(status='CANCELLED')
        .values_list('scheduled_start', flat=True)
    )
    
    data_dict = {}
    for dt in rows:
        hour = timezone.localtime(dt).hour
        data_dict[hour] = data_dict.get(hour, 0) + 1
        
    results = [{'hour': h, 'count': c} for h, c in data_dict.items()]
    results.sort(key=lambda x: x['count'], reverse=True)
    return results


def get_busiest_days(days_back=30):
    since_date = timezone.localdate() - timedelta(days=days_back)
    start_since, _ = get_day_bounds(since_date)
    
    rows = (
        Appointment.objects
        .filter(scheduled_start__gte=start_since)
        .exclude(status='CANCELLED')
        .values_list('scheduled_start', flat=True)
    )
    
    data_dict = {}
    for dt in rows:
        weekday = timezone.localtime(dt).isoweekday()
        django_weekday = (weekday % 7) + 1
        data_dict[django_weekday] = data_dict.get(django_weekday, 0) + 1
        
    results = [{'weekday': w, 'count': c} for w, c in data_dict.items()]
    results.sort(key=lambda x: x['count'], reverse=True)
    return results


def get_noshow_rate(days_back=30):
    since_date = timezone.localdate() - timedelta(days=days_back)
    start_since, _ = get_day_bounds(since_date)
    qs = Appointment.objects.filter(scheduled_start__gte=start_since)
    total = qs.exclude(status='CANCELLED').count()
    noshows = qs.filter(status='NO_SHOW').count()
    rate = round((noshows / total * 100), 1) if total > 0 else 0.0
    return {
        'total':   total,
        'noshows': noshows,
        'rate':    rate,
    }


def get_noshow_rate_per_doctor(days_back=30):
    since_date = timezone.localdate() - timedelta(days=days_back)
    start_since, _ = get_day_bounds(since_date)
    doctors = (
        Appointment.objects
        .filter(scheduled_start__gte=start_since)
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
        start_from, _ = get_day_bounds(date_from)
        qs = qs.filter(scheduled_start__gte=start_from)

    if date_to:
        _, end_to = get_day_bounds(date_to)
        qs = qs.filter(scheduled_start__lte=end_to)

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
    since_date = today - timedelta(days=years_back * 365)
    start_since, _ = get_day_bounds(since_date)
    rows = (
        Appointment.objects
        .filter(scheduled_start__gte=start_since)
        .values_list('scheduled_start', flat=True)
    )
    
    data_dict = {}
    for dt in rows:
        date_str = timezone.localtime(dt).date().isoformat()
        data_dict[date_str] = data_dict.get(date_str, 0) + 1
            
    results = []
    current_date = since_date
    while current_date <= today:
        results.append({
            'date': current_date,
            'count': data_dict.get(current_date.isoformat(), 0)
        })
        current_date += timedelta(days=1)
    return results

def get_revenue_all_dates(years_back=3):
    today = timezone.localdate()
    since_date = today - timedelta(days=years_back * 365)
    return _revenue_points_for_dates(since_date, today)


def get_revenue_all_months(years_back=3):
    today = timezone.localdate()
    since = today.replace(day=1) - timedelta(days=years_back * 365)
    since_dt = timezone.make_aware(datetime.combine(since.replace(day=1), time.min))
    
    rows = _completed_appointments_with_fees(scheduled_start__gte=since_dt)

    count_by_month = defaultdict(int)
    revenue_by_month = defaultdict(Decimal)
    for appt in rows:
        month_str = timezone.localtime(appt.scheduled_start).date().replace(day=1).isoformat()
        count_by_month[month_str] += 1
        revenue_by_month[month_str] += _appointment_fee(appt)
        
    results = []
    for month_str, count in sorted(count_by_month.items()):
        results.append({
            'date': datetime.fromisoformat(month_str).date(),
            'count': count,
            'revenue': float(revenue_by_month.get(month_str, Decimal("0.00"))),
        })
    return results
