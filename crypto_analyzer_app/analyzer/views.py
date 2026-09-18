from collections.abc import Callable
from typing import Any

from django.db.models import QuerySet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Coin, CoinPrice, Snapshot, WatchlistItem
from .permissions import IsAdminOrReadOnly
from .serializer import (
    CoinFilter,
    CoinPriceAnalyticSerializer,
    CoinSerializer,
    SnapshotSerializer,
    WatchlistInputSerializer,
    WatchlistOutputSerializer,
)
from .services import (
    get_cached_market_stats,
    get_cached_top_movers,
    get_cached_top_volume,
    remove_from_watchlist,
)
from .tasks import fetch_snapshot_task


class CoinPricePagination(CursorPagination):
    page_size = 10
    ordering = "-id"


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
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Получение деталей снимка",
        description="Возвращает один снимок с ценами",
        responses={200: SnapshotSerializer, 404: OpenApiResponse(description="Снимки не найдены")},
    )
    @method_decorator(cache_page(60 * 60))
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().retrieve(request, *args, **kwargs)


class CoinViewSet(ReadOnlyModelViewSet):
    tags = ["Coins"]
    permission_classes = [IsAdminOrReadOnly]
    queryset = Coin.objects.prefetch_related("prices").order_by("id")
    serializer_class = CoinSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CoinFilter
    search_fields = ["symbol", "name"]

    @action(detail=True, methods=["get"], pagination_class=CoinPricePagination)
    def history(self, request: Request, pk: str, version: str | None = None) -> Response:
        prices = CoinPrice.objects.filter(coin_id=pk)
        page = self.paginate_queryset(prices)

        if page is not None:
            serializer = CoinPriceAnalyticSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CoinPriceAnalyticSerializer(prices, many=True)
        return Response(serializer.data)


class WatchlistViewSet(ModelViewSet):
    tags = ["Watchlist"]
    permission_classes = [
        IsAuthenticated,
    ]

    def get_serializer_class(self) -> type[BaseSerializer]:
        if self.action in ("create", "delete_watchlist"):
            return WatchlistInputSerializer
        return WatchlistOutputSerializer

    def get_queryset(self) -> QuerySet[WatchlistItem]:
        if getattr(self, "swagger_fake_view", False):
            return WatchlistItem.objects.none()

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
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
    def delete_watchlist(self, request: Request, version: str | None = None) -> Response:
        symbol = request.data.get("symbol")
        result = remove_from_watchlist(request.user, symbol)

        if result.get("valid") is False:
            return Response(result, status=404)

        return Response(result, status=200)


class MarketStatusView(APIView):
    tags = ["Analytics"]

    @extend_schema(
        summary="Получить состояние рынка",
        responses={
            200: OpenApiResponse(description="Статистика рынка"),
            404: OpenApiResponse(description="Снимки не найдены"),
            429: OpenApiResponse(description="Превышен лимит запросов"),
        },
    )
    def get(self, request: Request, version: str | None = None) -> Response:
        data = get_cached_market_stats()

        if isinstance(data, dict) and "error" in data:
            raise NotFound("Снимков нет")

        return Response(data)


class TopAnalyticsView(APIView):
    source: Callable[..., Any] | None = None

    def get(self, request: Request, version: str | None = None) -> Response:
        if self.source is None:
            raise RuntimeError("Analytics source is not configured")

        data = self.source()

        if isinstance(data, dict) and "error" in data:
            raise NotFound("Снимков нет")

        serializer = CoinPriceAnalyticSerializer(data, many=True)
        return Response(serializer.data)


class TopMoversView(TopAnalyticsView):
    tags = ["Analytics"]
    source = staticmethod(get_cached_top_movers)

    @extend_schema(
        summary="Получить лидеров роста и падения",
        responses={
            200: CoinPriceAnalyticSerializer(many=True),
            404: OpenApiResponse(description="Снимки не найдены"),
            429: OpenApiResponse(description="Превышен лимит запросов"),
        },
    )
    def get(self, request: Request, version: str | None = None) -> Response:
        return super().get(request, version)


class VolumeTopView(TopAnalyticsView):
    tags = ["Analytics"]
    source = staticmethod(get_cached_top_volume)

    @extend_schema(
        summary="Получить лидеров по объёму",
        responses={
            200: CoinPriceAnalyticSerializer(many=True),
            404: OpenApiResponse(description="Снимки не найдены"),
            429: OpenApiResponse(description="Превышен лимит запросов"),
        },
    )
    def get(self, request: Request, version: str | None = None) -> Response:
        return super().get(request, version)


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
    def post(self, request: Request, version: str | None = None) -> Response:
        provider = request.data.get("provider", "coingecko")
        limit = request.data.get("limit", 3)

        task = fetch_snapshot_task.delay(provider, limit)

        return Response(
            {"task_id": task.id},
            status=202,
        )


class TaskStatusView(APIView):
    tags = ["Tasks"]

    @extend_schema(
        summary="Получить статус задачи",
        responses={
            200: OpenApiResponse(description="Статус задачи: PENDING/SUCCESS/FAILURE"),
            404: OpenApiResponse(description="Непредвиденная ошибка"),
        },
    )
    def get(self, request: Request, task_id: str, version: str | None = None) -> Response:
        result = fetch_snapshot_task.AsyncResult(task_id)

        return Response(
            {
                "status": result.status,
                "result": str(result.result) if result.failed() else result.result,
            }
        )
