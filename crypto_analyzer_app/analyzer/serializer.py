from django_filters import rest_framework as filters
from rest_framework import serializers

from .models import Coin, CoinPrice, Snapshot, WatchlistItem
from .services import add_to_watchlist, validate_symbol

# class CoinFilter(filters.FilterSet):
#     symbol = filters.CharFilter(lookup_expr="iexact")
#
#     class Meta:
#         model = Coin
#         fields = ["symbol"]


class CoinFilter(filters.FilterSet):
    symbol = filters.CharFilter(lookup_expr="iexact")
    min_price = filters.NumberFilter(method="filter_min_price", field_name="min_price", label="max price")
    max_price = filters.NumberFilter(method="filter_max_price", field_name="max_price", label="min price")

    class Meta:
        model = Coin
        fields = ["symbol", "min_price", "max_price"]

    def _latest_coin_ids(self, price_lookup):  # разабрать функцию
        last = Snapshot.objects.last()
        if not last:
            return Coin.objects.none()
        return CoinPrice.objects.filter(snapshot=last, **price_lookup).values_list("coin_id", flat=True)

    def filter_max_price(self, queryset, name, value):
        coin_ids = self._latest_coin_ids({"price__lte": value})
        return queryset.filter(id__in=coin_ids)

    def filter_min_price(self, queryset, name, value):
        coin_ids = self._latest_coin_ids({"price__gte": value})
        return queryset.filter(id__in=coin_ids)


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


class WatchlistInputSerializer(serializers.Serializer):
    symbol = serializers.CharField()

    def validate_symbol(self, value):
        result = validate_symbol(value)
        if not result:
            raise serializers.ValidationError(f"Монета {value} не найдена")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        symbol = validated_data["symbol"]
        return add_to_watchlist(user, symbol)


class WatchlistOutputSerializer(serializers.ModelSerializer):
    coin = serializers.StringRelatedField()

    class Meta:
        model = WatchlistItem
        fields = ["id", "coin", "added_at"]


class CoinPriceAnalyticSerializer(serializers.ModelSerializer):
    coin_name = serializers.CharField(source="coin.name", read_only=True)
    coin_symbol = serializers.CharField(source="coin.symbol", read_only=True)

    class Meta:
        model = CoinPrice
        fields = ["coin_name", "coin_symbol", "price", "volume_24h", "change_24h"]
