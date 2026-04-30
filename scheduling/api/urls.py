from rest_framework.routers import DefaultRouter

from scheduling.api.views import AppointmentSlotViewSet

app_name = "scheduling_api"

router = DefaultRouter()
router.register("slots", AppointmentSlotViewSet, basename="slot")

urlpatterns = router.urls
