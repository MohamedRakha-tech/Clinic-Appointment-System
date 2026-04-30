from django.urls import path
from django.views.generic import RedirectView

app_name = "appointments"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="accounts:patient_dashboard", permanent=False), name="list"),
]
