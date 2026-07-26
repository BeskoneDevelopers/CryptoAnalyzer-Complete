
from django.shortcuts import render

from rest_framework.viewsets import ModelViewSet

from .models import Snapshot
from .serializer import SnapshotSerializer

from rest_framework.pagination import PageNumberPagination

class SnapshotViewSet(ModelViewSet):
    queryset = Snapshot.objects.prefetch_related("coin_prices").all()
    serializer_class = SnapshotSerializer


