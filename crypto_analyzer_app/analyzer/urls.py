from django.http import JsonResponse
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CoinViewSet,
    MarketStatusView,
    PortfolioBuyView,
    PortfolioListView,
    PortfolioSellView,
    PortfolioSummaryView,
    SnapshotViewSet,
    StartSnapshotTaskView,
    TaskStatusView,
    TopMoversView,
    VolumeTopView,
    WatchlistViewSet,
)


def test_buy(request, version):
    return JsonResponse({"test": "django works"})


router = DefaultRouter()
router.register("snapshots", SnapshotViewSet, basename="snapshots")
router.register("coins", CoinViewSet, basename="coins")
(router.register("watchlist", WatchlistViewSet, basename="watchlist"),)


urlpatterns = [
    path("analytics/market-stats/", MarketStatusView.as_view(), name="market-stats"),
    path("analytics/top-movers/", TopMoversView.as_view(), name="top-movers"),
    path("analytics/volume-leaders/", VolumeTopView.as_view(), name="volume-leaders"),
    path("snapshots/start/", StartSnapshotTaskView.as_view(), name="snapshot-start"),
    path("snapshots/tasks/<str:task_id>/", TaskStatusView.as_view(), name="snapshot-task"),
    path("portfolio/", PortfolioListView.as_view(), name="portfolio-list"),
    path("portfolio/buy/", PortfolioBuyView.as_view(), name="portfolio-buy"),
    path("portfolio/sell/", PortfolioSellView.as_view(), name="portfolio-sell"),
    path("portfolio/summary/", PortfolioSummaryView.as_view(), name="portfolio-summary"),
] + router.urls
