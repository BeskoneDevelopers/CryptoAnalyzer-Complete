from rest_framework.routers import DefaultRouter
from .views import SnapshotViewSet

router = DefaultRouter()
router.register("snapshot", SnapshotViewSet, basename="snapshot")

urlpatterns = router.urls