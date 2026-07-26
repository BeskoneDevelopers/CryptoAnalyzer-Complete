from rest_framework import serializers
from .models import Coin, CoinPrice, Snapshot

from django_filters import rest_framework as filters

class CoinFilter(filters.FilterSet):
    symbol = filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = Coin
        fields = ["symbol"]



class CoinPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPrice
        fields = ["id", "coin", "snapshot", "price", "volume_24h", "change_24h"]


class CoinSerializer(serializers.ModelSerializer):
    prices = CoinPriceSerializer(many=True, read_only=True)

    class Meta:
        model = Coin
        fields = ["id", "name", "symbol", "prices"]



class SnapshotSerializer(serializers.ModelSerializer):
    coin_prices = CoinPriceSerializer(many=True, read_only=True)

    class Meta:
        model = Snapshot
        fields = ["id", "provider", "total_coins", "total_market_cap", "coin_prices"]



    #Секретка