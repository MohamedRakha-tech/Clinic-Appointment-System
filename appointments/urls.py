from django.urls import path
from . import views

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
    path('<int:pk>/no-show/', views.AppointmentNoShowView.as_view(), name='appointment-no-show'),
    
    # History
    path('<int:pk>/history/', views.AppointmentHistoryView.as_view(), name='appointment-history'),
]
