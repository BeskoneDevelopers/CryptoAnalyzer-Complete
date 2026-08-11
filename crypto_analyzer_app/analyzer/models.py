from django.db import models

class Coin(models.Model):
    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name_plural = "coins"

    def __str__(self):
        return self.name

class Snapshot(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    provider = models.CharField(max_length=255)
    total_coins = models.IntegerField()
    total_market_cap = models.DecimalField(max_digits=24, decimal_places=8)

    class Meta:
        verbose_name_plural = "snapshots"

    def __str__(self):
        return f"{self.created_at} - {self.provider} - {self.total_coins}"

class CoinPrice(models.Model):
    coin = models.ForeignKey(Coin, on_delete=models.CASCADE, related_name="prices")
    snapshot = models.ForeignKey(Snapshot, on_delete=models.CASCADE, related_name="prices")
    price = models.DecimalField(max_digits=24, decimal_places=8)
    volume_24h = models.DecimalField(max_digits=24, decimal_places=8)
    change_24h = models.DecimalField(max_digits=24, decimal_places=8, default=0)
    market_cap = models.DecimalField(max_digits=24, decimal_places=8, default=0)

    class Meta:
        verbose_name_plural = "coin_prices"
        unique_together = ["coin", "snapshot"]
        indexes = [
            models.Index(fields=["snapshot", "coin"])
        ]

    def __str__(self):
        return f"{self.coin.name} -> ${self.price}"