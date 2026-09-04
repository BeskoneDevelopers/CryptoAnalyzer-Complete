from celery.result import AsyncResult
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Coin, CoinPrice, Portfolio, Snapshot, WatchlistItem
from .permissions import IsAdminOrReadOnly
from .serializer import (
    CoinFilter,
    CoinPriceAnalyticSerializer,
    CoinSerializer,
    PortfolioSerializer,
    SnapshotSerializer,
    WatchlistInputSerializer,
    WatchlistOutputSerializer,
)
from .services import get_market_stats, get_top_movers, get_top_volume, remove_from_watchlist
from .tasks import fetch_snapshot_task


class CoinPricePagination(CursorPagination):
    page_size = 10
    ordering = "-snapshot__created_at"


class SnapshotViewSet(ReadOnlyModelViewSet):
    tags = ["Snapshots"]
    permission_classes = [IsAdminOrReadOnly]
    queryset = Snapshot.objects.prefetch_related("coin_prices").all()
    serializer_class = SnapshotSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["created_at", "total_market_cap"]
    ordering = ["-created_at"]

    @extend_schema(
        summary="Получение списка снимков рынка",
        description="Возвращает снимки с пагинациней",
        parameters=[
            OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, description="Номер страницы", required=False),
        ],
        responses={
            200: SnapshotSerializer(many=True),
            401: OpenApiResponse(description="Не авторизован"),
            429: OpenApiResponse(description="Превышен лимит запросов"),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Получение деталей снимка",
        description="Возвращает один снимок с ценами",
        responses={200: SnapshotSerializer, 404: OpenApiResponse(description="Снимки не найдены")},
    )
    @method_decorator(cache_page(60 * 60))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class CoinViewSet(ReadOnlyModelViewSet):
    tags = ["Coins"]
    permission_classes = [IsAdminOrReadOnly]
    queryset = Coin.objects.prefetch_related("prices").all()
    serializer_class = CoinSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CoinFilter
    search_fields = ["symbol", "name"]

    @action(detail=True, methods=["get"], pagination_class=CoinPricePagination)
    def history(self, request, pk=None):
        prices = CoinPrice.objects.filter(coin_id=pk)
        serializer = CoinPriceAnalyticSerializer(prices, many=True)
        return Response(serializer.data)


class WatchlistViewSet(ModelViewSet):
    tags = ["Watchlist"]
    permission_classes = [
        IsAuthenticated,
    ]

    def get_serializer_class(self):
        if self.action in ("create", "delete_watchlist"):
            return WatchlistInputSerializer
        return WatchlistOutputSerializer

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user).select_related("coin")

    @extend_schema(
        summary="Добавление монеты в Watchlist",
        request=WatchlistInputSerializer,
        responses={
            201: WatchlistOutputSerializer,
            400: OpenApiResponse(description="Ошибка валидации"),
            401: OpenApiResponse(description="Не авторизован"),
            404: OpenApiResponse(description="Непредвиденная ошибка"),
            429: OpenApiResponse(description="Превышен лимит запросов"),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        output_serializer = WatchlistOutputSerializer(instance)

        return Response(output_serializer.data, status=201)

    @extend_schema(
        summary="Удалить монету из Watchlist",
        responses={
            200: OpenApiResponse(description="Успешно удалено"),
            401: OpenApiResponse(description="Не авторизован"),
            404: OpenApiResponse(description="Непредвиденная ошибка"),
        },
    )
    @action(detail=False, methods=["delete"], url_path="remove")
    def delete_watchlist(self, request):
        symbol = request.data.get("symbol")
        result = remove_from_watchlist(request.user, symbol)
        return Response(result)


class MarketStatusView(APIView):
    tags = ["Analytics"]

    def get(self, request, version=None):
        cached_status = cache.get("market_stats")
        if cached_status is not None:
            return Response(cached_status)

        stats = get_market_stats()
        if "error" in stats:
            return Response(stats, status=404)

        cache.set("market_stats", stats, 4200)
        return Response(stats)


class TopMoversView(APIView):
    tags = ["Analytics"]

    def get(self, request, version=None):
        cached_status = cache.get("top_movers")
        if cached_status is not None:
            return Response(cached_status)
        move = get_top_movers()

        if isinstance(move, dict) and "error" in move:
            return Response(move, status=404)
        serializer = CoinPriceAnalyticSerializer(move, many=True)
        cache.set("top_movers", serializer.data, 4200)
        return Response(serializer.data)


class VolumeTopView(APIView):
    tags = ["Analytics"]

    def get(self, request, version=None):
        cached_status = cache.get("volume_leaders")

        if cached_status is not None:
            return Response(cached_status)

        toper = get_top_volume()

        if isinstance(toper, dict) and "error" in toper:
            return Response(toper, status=404)

        serializer = CoinPriceAnalyticSerializer(toper, many=True)
        cache.set("volume_leaders", serializer.data, 4200)

        return Response(serializer.data)


class StartSnapshotTaskView(APIView):
    tags = ["Tasks"]
    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(
        summary="Запуск сбора снимков",
        request=OpenApiTypes.OBJECT,
        responses={
            202: OpenApiResponse(description="Снимки собраны"),
            401: OpenApiResponse(description="Не авторизован"),
            429: OpenApiResponse(description="Превышен лимит запросов"),
        },
    )
    def post(self, request, version=None):
        provider = request.data.get("provider", "coingecko")
        limit = request.data.get("limit", 3)
        task = fetch_snapshot_task.delay(provider, limit)
        return Response({"task_id": task.id}, status=202)


class TaskStatusView(APIView):
    tags = ["Tasks"]

    @extend_schema(
        summary="Получить статус задачи",
        responses={
            200: OpenApiResponse(description="Статус задачи: PENDING/SUCCESS/FAILURE"),
            404: OpenApiResponse(description="Непредвиденная ошибка"),
        },
    )
    def get(self, request, task_id, version=None):
        result = AsyncResult(task_id)
        return Response({"status": result.status, "result": result.result})


class PortfolioListView(ListAPIView):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        portfolio = Portfolio.objects.filter(user=self.request.user)
        return portfolio

    def get_serializer_context(self):
        context = super().get_serializer_context()
        portfolio = self.get_queryset()
        latest_snapshot = Snapshot.objects.order_by("-created_at").first()

        if latest_snapshot is None:
            raise NotFound("Снимок рынка не найден")

        coin_ids = portfolio.values_list("coin_id", flat=True)

        prices = CoinPrice.objects.filter(snapshot=latest_snapshot, coin_id__in=coin_ids)

        context["prices"] = {price.coin_id: price.price for price in prices}
        return context
