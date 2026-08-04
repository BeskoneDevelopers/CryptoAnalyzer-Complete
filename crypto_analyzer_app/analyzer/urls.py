from rest_framework.routers import DefaultRouter
from .views import SnapshotViewSet,CoinViewSet

router = DefaultRouter()
router.register("snapshots", SnapshotViewSet, basename="snapshots")
router.register("coins", CoinViewSet, basename="coins")

urlpatterns = router.urls