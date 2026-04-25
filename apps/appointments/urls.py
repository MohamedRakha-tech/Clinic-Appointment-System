from django.urls import path
from apps.appointments.views import (
    appointment_list, appointment_detail, book_appointment,
    update_appointment_status, reschedule_appointment, search_appointments
)

app_name = 'appointments'

urlpatterns = [
    path('', appointment_list, name='appointment_list'),
    path('search/', search_appointments, name='search_appointments'),
    path('book/', book_appointment, name='book_appointment'),
    path('<int:pk>/', appointment_detail, name='appointment_detail'),
    path('<int:pk>/confirm/', update_appointment_status, {'action': 'confirm'}, name='confirm_appointment'),
    path('<int:pk>/check-in/', update_appointment_status, {'action': 'check_in'}, name='check_in_appointment'),
    path('<int:pk>/complete/', update_appointment_status, {'action': 'complete'}, name='complete_appointment'),
    path('<int:pk>/cancel/', update_appointment_status, {'action': 'cancel'}, name='cancel_appointment'),
    path('<int:pk>/no-show/', update_appointment_status, {'action': 'no_show'}, name='no_show_appointment'),
    path('<int:pk>/reschedule/', reschedule_appointment, name='reschedule_appointment'),
]
