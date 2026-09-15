from decimal import Decimal
from typing import Any

from django.db.models import QuerySet
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.request import Request

from .models import Coin, CoinPrice, Portfolio, Snapshot, WatchlistItem
from .services import add_to_watchlist
from .services import validate_symbol as service_validate_symbol


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

    def _latest_coin_ids(self, price_lookup: dict[str, Any]) -> QuerySet[CoinPrice, int]:
        if not hasattr(self, "snapshot"):
            self.snapshot = Snapshot.objects.last()

        if not self.snapshot:
            return CoinPrice.objects.none().values_list("coin_id", flat=True)

        return CoinPrice.objects.filter(snapshot=self.snapshot, **price_lookup).values_list("coin_id", flat=True)

    def filter_max_price(self, queryset: QuerySet[Coin], name: str, value: Any) -> QuerySet[Coin]:
        coin_ids = self._latest_coin_ids({"price__lte": value})
        return queryset.filter(id__in=coin_ids)

    def filter_min_price(self, queryset: QuerySet[Coin], name: str, value: Any) -> QuerySet[Coin]:
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

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        symbol = attrs["symbol"].strip().lower()

        result = service_validate_symbol(symbol)

        if not result:
            raise serializers.ValidationError(f"Монета {symbol} не найдена")

        attrs["symbol"] = symbol
        attrs["coin_data"] = result

        return attrs

    def create(self, validated_data: dict[str, Any]) -> WatchlistItem:
        request: Request = self.context["request"]
        user = request.user

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


class PortfolioSerializer(serializers.ModelSerializer):
    coin = serializers.SerializerMethodField()
    symbol = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = ["coin", "symbol", "amount", "buy_price", "current_price", "current_value"]

    def get_coin(self, obj):
        return obj.coin.name

    def get_symbol(self, obj):
        return obj.coin.symbol.upper()

    def _get_current_price(self, obj: Portfolio) -> Decimal | None:
        prices = self.context.get("prices", {})
        return prices.get(obj.coin_id)

    def get_current_price(self, obj: Portfolio) -> Decimal | None:
        return self._get_current_price(obj)

    def get_current_value(self, obj: Portfolio) -> Decimal | None:
        price = self._get_current_price(obj)

        if price is None:
            return None

        return obj.amount * price


class PortfolioBuySerializer(serializers.Serializer):
    coin = serializers.PrimaryKeyRelatedField(queryset=Coin.objects.all())
    amount = serializers.DecimalField(
        max_digits=24,
        decimal_places=12,
    )


class PortfolioSellSerializer(serializers.Serializer):
    coin = serializers.PrimaryKeyRelatedField(queryset=Coin.objects.all())
    amount = serializers.DecimalField(
        max_digits=24,
        decimal_places=12,
        min_value=Decimal("0.000000000001"),
    )


class PortfolioSummarySerializer(serializers.Serializer):
    balance = serializers.DecimalField(
        max_digits=36,
        decimal_places=12,
    )
    portfolio_value = serializers.DecimalField(
        max_digits=36,
        decimal_places=12,
    )
    total_value = serializers.DecimalField(
        max_digits=36,
        decimal_places=12,
    )
