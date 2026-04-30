
from django.utils import timezone

from .models import AuditLog

from . import selectors



def _fmt(value):
    if value >= 1_000_000:
        return f'${value / 1_000_000:.2f}M'
    if value >= 1_000:
        return f'${value / 1_000:.1f}K'
    return f'${value}'


def get_admin_dashboard_data():
    noshow           = selectors.get_noshow_rate(days_back=30)
    monthly_rev      = selectors.get_monthly_revenue()
    total_rev        = selectors.get_total_revenue()
    total_completed  = selectors.get_total_completed_count()

    return {
        'today_appointments':     selectors.get_today_appointments_count(),
        'pending_count':          selectors.get_pending_appointments_count(),
        'total_patients':         selectors.get_total_patients_count(),
        'total_doctors':          selectors.get_total_doctors_count(),
        'new_patients_month':     selectors.get_new_patients_this_month(),
        'monthly_revenue':        monthly_rev,
        'monthly_revenue_fmt':    _fmt(monthly_rev),
        'total_revenue':          total_rev,
        'total_revenue_fmt':      _fmt(total_rev),
        'total_completed':        total_completed,
        'noshow_rate':            noshow['rate'],
        'noshow_count':           noshow['noshows'],
        'noshow_summary':         noshow,
        'appointments_by_status': selectors.get_appointments_by_status(),
        'appointments_last_30':   list(selectors.get_appointments_last_n_days(30)),
        'revenue_last_6_months':  list(selectors.get_revenue_last_n_months(6)),
        'peak_hours':             list(selectors.get_peak_hours()),
        'busiest_days':           list(selectors.get_busiest_days()),
        'top_doctors':            list(selectors.get_top_doctors(limit=5)),
        'noshow_per_doctor':      selectors.get_noshow_rate_per_doctor(),
        'recent_audit_logs':      selectors.get_recent_audit_logs(limit=8),
    }



def get_doctor_dashboard_data(doctor_user):
    noshow = selectors.get_noshow_rate_per_doctor(days_back=30)
    my_noshow = next(
        (d for d in noshow if d['doctor_id'] == doctor_user.id),
        {'rate': 0.0, 'noshows': 0, 'total': 0}
    )

    return {
        'today_queue': selectors.get_doctor_today_queue(doctor_user.id),
        'my_noshow_rate':  my_noshow['rate'],
        'my_noshow_count': my_noshow['noshows'],
        'my_total_month':  my_noshow['total'],
    }



def get_receptionist_dashboard_data():

    return {
        'today_appointments': selectors.get_today_appointments_count(),
        'pending_count':      selectors.get_pending_appointments_count(),
        'appointments_today': selectors.get_appointments_by_status(date=timezone.localdate()),
        'appointments_list':  selectors.get_today_appointments_list(),
    }


def log_action(
    action,
    instance=None,
    target_model=None,
    target_id=None,
    description='',
    extra_data=None,
):
    from dashboard.middleware import get_current_user, get_current_request

    if instance is not None:
        model_name = instance.__class__.__name__
        obj_id     = getattr(instance, 'pk', None)
    else:
        model_name = target_model or 'Unknown'
        obj_id     = target_id

    if model_name == 'AuditLog':
        return

    user = get_current_user()
    if user and not user.is_authenticated:
        user = None

    ip      = None
    request = get_current_request()
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')

    AuditLog.log(
        user=user,
        action=action,
        target_model=model_name,
        target_id=obj_id,
        description=description,
        ip_address=ip,
        extra_data=extra_data or {},
    )