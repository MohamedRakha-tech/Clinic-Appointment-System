from rest_framework.routers import SimpleRouter

from appointments.api.views import AppointmentViewSet

app_name = "appointments_api"

router = SimpleRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls
