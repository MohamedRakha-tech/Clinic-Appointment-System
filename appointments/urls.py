from django.urls import path
from . import views

# app_name = "appointments"

urlpatterns = [
    # List and Detail
    path('', views.AppointmentListView.as_view(), name='appointment-list'),
    path('<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
    
    # Booking
    path('book/', views.AppointmentBookView.as_view(), name='appointment-book'),
    
    # Actions
    path('<int:pk>/cancel/', views.AppointmentCancelView.as_view(), name='appointment-cancel'),
    path('<int:pk>/reschedule/', views.AppointmentRescheduleView.as_view(), name='appointment-reschedule'),
    path('<int:pk>/confirm/', views.AppointmentConfirmView.as_view(), name='appointment-confirm'),
    path('<int:pk>/complete/', views.AppointmentCompleteView.as_view(), name='appointment-complete'),
    path('<int:pk>/decline/', views.AppointmentDeclineView.as_view(), name='appointment-decline'),
    path('<int:pk>/no-show/', views.AppointmentNoShowView.as_view(), name='appointment-no-show'),
    path('<int:pk>/check-in/', views.AppointmentCheckInView.as_view(), name='appointment-check-in'),
    path('<int:pk>/complete/', views.AppointmentCompleteView.as_view(), name='appointment-complete'),
    
    # History
    path('<int:pk>/history/', views.AppointmentHistoryView.as_view(), name='appointment-history'),
]
