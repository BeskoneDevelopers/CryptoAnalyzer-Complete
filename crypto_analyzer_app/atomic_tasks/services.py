from decimal import Decimal

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction

from analyzer.models import Balance, Coin, CoinPrice, Portfolio, Snapshot
from analyzer.services import get_latest_price


class PortfolioService:
    @staticmethod
    def buy(user: AbstractBaseUser, coin: Coin, amount: Decimal):
        if amount <= 0:
            raise ValueError("Неверно указано количество")
        with transaction.atomic():
            balance = Balance.objects.select_for_update().get(user=user)
            price = get_latest_price(coin)
            cost = amount * price
            new_balance = balance.amount - cost
            if new_balance < 0:
                raise ValueError("Недостаточно средств")
            balance.amount = new_balance
            balance.save()

            portfolio, created = Portfolio.objects.get_or_create(user=user, coin=coin, defaults={"amount": amount, "buy_price": price})
            if not created:
                old_amount = portfolio.amount
                old_price = portfolio.buy_price

                portfolio.amount = old_amount + amount
                avg_price = (old_price * old_amount + cost) / portfolio.amount
                portfolio.buy_price = avg_price
                portfolio.save()

        return {"successful": "Операция прошла успешно"}

    @staticmethod
    def sell(user: AbstractBaseUser, coin: Coin, amount: Decimal):
        if amount <= 0:
            raise ValueError("Неверно указано количество")
        with transaction.atomic():
            balance = Balance.objects.select_for_update().get(user=user)

            price = get_latest_price(coin)
            cost = amount * price
            new_balance = balance.amount + cost
            balance.amount = new_balance
            balance.save()

            try:
                portfolio = Portfolio.objects.get(user=user, coin=coin)
            except Portfolio.DoesNotExist:
                raise ValueError("Позиция отсутствует")

            old_amount = portfolio.amount

            portfolio.amount = old_amount - amount
            if portfolio.amount < 0:
                raise ValueError("Недостаточно монет в портфеле")
            elif portfolio.amount == 0:
                portfolio.delete()
            else:
                portfolio.save()
        return {"successful": "Операция прошла успешно"}

    @staticmethod
    def get_summary(user):
        balance = Balance.objects.get(user=user)

        latest_snapshot = Snapshot.objects.order_by("-created_at").first()
        if latest_snapshot is None:
            raise ValueError("Снимок рынка не найден")

        positions = Portfolio.objects.filter(user=user)

        coin_ids = positions.values_list("coin_id", flat=True)

        prices = CoinPrice.objects.filter(
            snapshot=latest_snapshot,
            coin_id__in=coin_ids,
        )

        prices_map = {price.coin_id: price.price for price in prices}

        portfolio_value = Decimal("0")

        for position in positions:
            price = prices_map.get(position.coin_id)

            if price is None:
                raise ValueError(f"Цена монеты {position.coin_id} не найдена")

            portfolio_value += position.amount * price

        total_value = balance.amount + portfolio_value

        return {
            "balance": balance.amount,
            "portfolio_value": portfolio_value,
            "total_value": total_value,
        }
