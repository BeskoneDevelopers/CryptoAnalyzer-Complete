from decimal import Decimal

from analyzer.models import Balance, Coin, Portfolio
from analyzer.services import get_latest_price, get_latest_prices
from django.contrib.auth.models import User
from django.db import transaction


class PortfolioService:
    @staticmethod
    def buy(user: User, coin: Coin, amount: Decimal):
        if amount <= 0:
            raise ValueError("Неверно указано количество")
        with transaction.atomic():
            try:
                balance = Balance.objects.select_for_update().get(user=user)
            except Balance.DoesNotExist:
                raise ValueError("Баланс пользователя не найден") from None

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
    def sell(user: User, coin: Coin, amount: Decimal):
        if amount <= 0:
            raise ValueError("Неверно указано количество")
        with transaction.atomic():
            try:
                balance = Balance.objects.select_for_update().get(user=user)
            except Balance.DoesNotExist:
                raise ValueError("Баланс пользователя не найден") from None

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
    def get_summary(user: User):
        with transaction.atomic():
            try:
                balance = Balance.objects.select_for_update().get(user=user)
            except Balance.DoesNotExist:
                raise ValueError("Баланс пользователя не найден") from None

            positions = Portfolio.objects.filter(user=user)
            coin_ids = positions.values_list("coin_id", flat=True)
            prices_map = get_latest_prices(coin_ids)

            purchase_value = Decimal("0")
            calculated_portfolio_value = Decimal("0")
            has_missing_price = False

            for position in positions:
                purchase_value += position.amount * position.buy_price

                price = prices_map.get(position.coin_id)

                if price is None:
                    has_missing_price = True
                    continue

                calculated_portfolio_value += position.amount * price

            portfolio_value: Decimal | None
            profit_loss: Decimal | None
            total_value: Decimal | None

            if has_missing_price:
                portfolio_value = None
                profit_loss = None
                total_value = None
            else:
                portfolio_value = calculated_portfolio_value
                profit_loss = portfolio_value - purchase_value
                total_value = balance.amount + portfolio_value

            return {
                "balance": balance.amount,
                "purchase_value": purchase_value,
                "portfolio_value": portfolio_value,
                "profit_loss": profit_loss,
                "total_value": total_value,
            }
