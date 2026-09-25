from rest_framework import serializers
from .models import Coin, CoinPrice, Snapshot, WatchlistItem

from django_filters import rest_framework as filters

from .services import (validate_symbol as service_validate_symbol,add_to_watchlist,get_latest_snapshot)

class CoinFilter(filters.FilterSet):
    symbol = filters.CharFilter(lookup_expr="iexact")
    min_price = filters.NumberFilter(
        method="filter_min_price",
        field_name="min_price",
        label="min price",
    )
    max_price = filters.NumberFilter(
        method="filter_max_price",
        field_name="max_price",
        label="max price",
    )

    class Meta:
        model = Coin
        fields = ["symbol", "min_price", "max_price"]

    def _latest_coin_ids(self, price_lookup):
        if not hasattr(self, "snapshot"):
            self.snapshot = get_latest_snapshot()

        if not self.snapshot:
            return Coin.objects.none()

        return CoinPrice.objects.filter(
            snapshot=self.snapshot,
            **price_lookup,
        ).values_list("coin_id", flat=True)

    def filter_max_price(self, queryset, name, value):
        coin_ids = self._latest_coin_ids({"price__lte": value})
        return queryset.filter(id__in=coin_ids)

    def filter_min_price(self, queryset, name, value):
        coin_ids = self._latest_coin_ids({"price__gte": value})
        return queryset.filter(id__in=coin_ids)




class CoinPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPrice
        fields = [
            "id",
            "coin",
            "snapshot",
            "price",
            "volume_24h",
            "change_24h",
            "market_cap",
        ]


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

    def validate(self, attrs):
        symbol = attrs["symbol"].strip().upper()

        result = service_validate_symbol(symbol)

        if not result:
            raise serializers.ValidationError(
                f"Монета {symbol} не найдена"
            )

        attrs["symbol"] = symbol
        attrs["coin_data"] = result

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        return add_to_watchlist(
            user=user,
            symbol=validated_data["symbol"],
            coin_data=validated_data["coin_data"],
        )

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