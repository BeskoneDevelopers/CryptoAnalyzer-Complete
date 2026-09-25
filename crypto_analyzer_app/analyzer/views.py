from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Coin, Snapshot, WatchlistItem
from .serializer import (
    CoinFilter,
    CoinPriceAnalyticSerializer,
    CoinSerializer,
    SnapshotSerializer,
    WatchlistInputSerializer,
    WatchlistOutputSerializer,
)
from .services import (
    get_market_stats,
    remove_from_watchlist,
)
from .tasks import fetch_snapshot_task


class SnapshotViewSet(ReadOnlyModelViewSet):
    queryset = Snapshot.objects.prefetch_related("coin_prices").all()
    serializer_class = SnapshotSerializer


class CoinViewSet(ReadOnlyModelViewSet):
    queryset = (
        Coin.objects
        .prefetch_related("prices")
        .order_by("id")
    )
    serializer_class = CoinSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = CoinFilter


class WatchlistViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action in ("create", "delete_watchlist"):
            return WatchlistInputSerializer
        return WatchlistOutputSerializer

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user).select_related("coin")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        output_serializer = WatchlistOutputSerializer(instance)

        return Response(output_serializer.data, status=201)

    @action(detail=False, methods=["delete"], url_path="remove")
    def delete_watchlist(self, request):
        symbol = request.data.get("symbol")
        result = remove_from_watchlist(request.user, symbol)

        if result.get("valid") is False:
            return Response(result, status=404)

        return Response(result, status=200)


class MarketStatusView(APIView):
    def get(self, request):
        stats = get_market_stats()
        if "error" in stats:
            return Response(stats, status=404)
        return Response(stats)


class TopAnalyticsView(APIView):
    source = None

    def get(self, request):
        data = self.source()

        if isinstance(data, dict) and "error" in data:
            return Response(data, status=404)

        serializer = CoinPriceAnalyticSerializer(data, many=True)
        return Response(serializer.data)


class StartSnapshotTaskView(APIView):
    def post(self, request):
        provider = request.data.get("provider", "coingecko")
        limit = request.data.get("limit", 3)

        task = fetch_snapshot_task.delay(provider, limit)

        return Response(
            {"task_id": task.id},
            status=202,
        )


class TaskStatusView(APIView):
    def get(self, request, task_id):
        result = fetch_snapshot_task.AsyncResult(task_id)

        return Response({
            "status": result.status,
            "result": str(result.result) if result.failed() else result.result,
        })
