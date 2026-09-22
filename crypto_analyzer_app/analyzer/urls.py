from rest_framework.routers import DefaultRouter
from .views import SnapshotViewSet,CoinViewSet, WatchlistViewSet

router = DefaultRouter()
router.register("snapshots", SnapshotViewSet, basename="snapshots")
router.register("coins", CoinViewSet, basename="coins")
router.register("watchlist", WatchlistViewSet, basename="watchlist")

urlpatterns = router.urls