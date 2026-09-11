from rest_framework import serializers
from .models import Coin, CoinPrice, Snapshot, WatchlistItem

from django_filters import rest_framework as filters

from .services import validate_symbol as service_validate_symbol, add_to_watchlist

class CoinFilter(filters.FilterSet):
    symbol = filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = Coin
        fields = ["symbol"]



class CoinPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPrice
        fields = ["id", "coin", "snapshot", "price", "volume_24h", "change_24h", "market_cap"]


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
        symbol = attrs["symbol"].strip().lower()

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
