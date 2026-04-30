import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clinic.settings")
django.setup()

from dashboard.selectors import get_appointments_last_n_days, get_revenue_last_n_days, get_appointments_all_dates

print("Last 7 days:")
print(get_appointments_last_n_days(7))
print("Last 7 days revenue:")
print(get_revenue_last_n_days(7))
