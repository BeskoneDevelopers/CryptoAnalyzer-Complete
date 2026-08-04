
from django.shortcuts import render
from django_filters import rest_framework as filters
from rest_framework.viewsets import ModelViewSet

from .models import Snapshot, Coin
from .serializer import SnapshotSerializer, CoinSerializer, CoinFilter


class SnapshotViewSet(ModelViewSet):
    queryset = Snapshot.objects.prefetch_related("coin_prices").all()
    serializer_class = SnapshotSerializer


class CoinViewSet(ModelViewSet):
    queryset = Coin.objects.all()
    serializer_class = CoinSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CoinFilter
