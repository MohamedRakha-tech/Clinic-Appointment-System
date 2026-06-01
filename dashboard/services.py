from django.utils import timezone

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

    appointments_by_status = selectors.get_appointments_by_status()
    total_status_appointments = sum(appointments_by_status.values())

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
        'appointments_by_status': appointments_by_status,
        'total_status_appointments': total_status_appointments,
        'appointments_last_30':   list(selectors.get_appointments_last_n_days(30)),
        'revenue_last_6_months':  list(selectors.get_revenue_last_n_months(6)),
        'peak_hours':             list(selectors.get_peak_hours()),
        'busiest_days':           list(selectors.get_busiest_days()),
        'top_doctors':            list(selectors.get_top_doctors(limit=5)),
        'noshow_per_doctor':      selectors.get_noshow_rate_per_doctor(),
    }



def get_doctor_dashboard_data(doctor_user):
    noshow = selectors.get_noshow_rate_per_doctor(days_back=30)
    my_noshow = next(
        (d for d in noshow if d['doctor_id'] == doctor_user.id),
        {'rate': 0.0, 'noshows': 0, 'total': 0}
    )
    today_status = selectors.get_doctor_today_status_summary(doctor_user.id)

    return {
        'today_queue': selectors.get_doctor_today_queue(doctor_user.id),
        'today_schedule': selectors.get_doctor_today_schedule(doctor_user.id),
        'today_queue_count': selectors.get_doctor_today_queue_count(doctor_user.id),
        'requested_today_count': selectors.get_doctor_requested_today_count(doctor_user.id),
        'confirmed_today_count': selectors.get_doctor_confirmed_today_count(doctor_user.id),
        'completed_today_count': selectors.get_doctor_completed_today_count(doctor_user.id),
        'upcoming_today_count': selectors.get_doctor_upcoming_today_count(doctor_user.id),
        'my_noshow_rate':  my_noshow['rate'],
        'my_noshow_count': my_noshow['noshows'],
        'my_total_month':  my_noshow['total'],
        'today_status': today_status,
    }



def get_receptionist_dashboard_data():
    appointments_today = selectors.get_appointments_by_status(date=timezone.localdate())
    pending_count = selectors.get_pending_appointments_count()
    checked_in_count = appointments_today.get('CHECKED_IN', 0)
    completed_count = appointments_today.get('COMPLETED', 0)

    return {
        'today_appointments': selectors.get_today_appointments_count(),
        'pending_count':      pending_count,
        'checked_in_count':   checked_in_count,
        'completed_count':    completed_count,
        'appointments_today': appointments_today,
        'appointments_list':  selectors.get_today_appointments_list(),
        'reception_focus': (
            {
                'tone': 'action',
                'title': f'{pending_count} appointment{"s" if pending_count != 1 else ""} awaiting confirmation',
                'message': 'Start with the appointments list to confirm or decline pending requests.',
            }
            if pending_count
            else {
                'tone': 'live' if checked_in_count else 'calm',
                'title': (
                    f'{checked_in_count} patient{"s" if checked_in_count != 1 else ""} checked in'
                    if checked_in_count else 'Front desk is under control'
                ),
                'message': (
                    'Use the queue monitor to coordinate live patient flow across doctors.'
                    if checked_in_count else 'No pending confirmations right now. You can monitor queue flow or book new visits.'
                ),
            }
        ),
    }
