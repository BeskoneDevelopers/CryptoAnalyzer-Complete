from django.urls import path
from rest_framework.routers import DefaultRouter

from .services import get_top_movers, get_top_volume
from .views import (
    CoinViewSet,
    MarketStatusView,
    SnapshotViewSet,
    StartSnapshotTaskView,
    TaskStatusView,
    TopAnalyticsView,
    WatchlistViewSet,
)

router = DefaultRouter()
router.register("snapshots", SnapshotViewSet, basename="snapshots")
router.register("coins", CoinViewSet, basename="coins")
router.register("watchlist", WatchlistViewSet, basename="watchlist")

urlpatterns = [
    path(
        "analytics/market-stats/",
        MarketStatusView.as_view(),
        name="market-stats",
    ),
    path(
        "analytics/top-movers/",
        TopAnalyticsView.as_view(source=get_top_movers),
        name="top-movers",
    ),
    path(
        "analytics/volume-leaders/",
        TopAnalyticsView.as_view(source=get_top_volume),
        name="volume-leaders",
    ),
    path(
        "snapshots/start/",
        StartSnapshotTaskView.as_view(),
        name="snapshot-start",
    ),
    path(
        "snapshots/tasks/<str:task_id>/",
        TaskStatusView.as_view(),
        name="snapshot-task",
    ),
] + router.urls