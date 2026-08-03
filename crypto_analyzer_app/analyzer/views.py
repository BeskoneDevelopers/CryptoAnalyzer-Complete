from rest_framework.decorators import action
from  rest_framework.response import Response
from django.shortcuts import render
from django_filters import rest_framework as filters

from rest_framework.viewsets import ModelViewSet

from rest_framework.permissions import IsAuthenticated

from .models import Snapshot, Coin, WatchlistItem
from .serializer import SnapshotSerializer, CoinSerializer, CoinFilter, WatchlistInputSerializer, WatchlistOutputSerializer
from .services import remove_from_watchlist


class SnapshotViewSet(ModelViewSet):
    queryset = Snapshot.objects.prefetch_related("coin_prices").all()
    serializer_class = SnapshotSerializer


class CoinViewSet(ModelViewSet):
    queryset = Coin.objects.all()
    serializer_class = CoinSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CoinFilter

class WatchlistViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated,]

    def get_serializer_class(self):
        if self.action in ("create", "delete_watchlist"):
            return WatchlistInputSerializer
        return WatchlistOutputSerializer

    def get_queryset(self):
        return WatchlistItem.objects.filter(user=self.request.user)

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
        return Response(result)
