from django.contrib import admin

from .models import Balance, Coin, CoinPrice, Portfolio, Snapshot


@admin.register(Coin)
class CoinAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "symbol",
    )
    list_display_links = ("id", "name")
    search_fields = ["name", "symbol"]


class CoinPriceInline(admin.TabularInline):
    model = CoinPrice
    extra = 1
    fields = ["coin", "price", "volume_24h", "change_24h"]


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "provider", "total_coins", "total_market_cap")
    inlines = [CoinPriceInline]


@admin.register(CoinPrice)
class CoinPriceAdmin(admin.ModelAdmin):
    list_display = ("coin", "snapshot", "price", "volume_24h", "change_24h")
    list_filter = ["snapshot", "coin"]


@admin.register(Balance)
class BalanceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount")
    list_filter = ["user"]


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("user", "coin", "amount", "buy_price")
    list_filter = ["user"]
