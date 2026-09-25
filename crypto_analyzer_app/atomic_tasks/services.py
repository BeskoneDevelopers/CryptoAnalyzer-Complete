from decimal import Decimal

import structlog
from analyzer.models import Balance, Coin, Portfolio
from analyzer.services import get_latest_price, get_latest_prices
from django.contrib.auth.models import User
from django.db import transaction

logger = structlog.get_logger(__name__)


class PortfolioService:
    @staticmethod
    def buy(user: User, coin: Coin, amount: Decimal) -> dict[str, str]:
        with transaction.atomic():
            try:
                balance = Balance.objects.select_for_update().get(user=user)
            except Balance.DoesNotExist:
                logger.warning("buy_coin_failed", user_id=user.id, symbol=coin.symbol, amount=str(amount), reason="balance_not_found")
                raise ValueError("Баланс пользователя не найден") from None

            price = get_latest_price(coin)
            cost = amount * price
            new_balance = balance.amount - cost

            if new_balance < 0:
                logger.warning(
                    "buy_coin_failed", user_id=user.id, symbol=coin.symbol.upper(), amount=str(amount), reason="insufficient_funds"
                )
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

            transaction.on_commit(
                lambda: logger.info(
                    "buy_coin", user_id=user.id, symbol=coin.symbol, amount=str(amount), price=str(price), cost=str(cost)
                )
            )

        return {"successful": "Операция прошла успешно"}

    @staticmethod
    def sell(user: User, coin: Coin, amount: Decimal) -> dict[str, str]:
        with transaction.atomic():
            try:
                balance = Balance.objects.select_for_update().get(user=user)
            except Balance.DoesNotExist:
                logger.warning("sell_coin_failed", user_id=user.id, symbol=coin.symbol, amount=str(amount), reason="balance_not_found")
                raise ValueError("Баланс пользователя не найден") from None

            try:
                portfolio = Portfolio.objects.select_for_update().get(user=user, coin=coin)

            except Portfolio.DoesNotExist:
                logger.warning(
                    "sell_coin_failed", user_id=user.id, symbol=coin.symbol, amount=str(amount), reason="position_not_found"
                )
                raise ValueError("Позиция отсутствует")

            old_amount = portfolio.amount

            portfolio.amount = old_amount - amount

            if portfolio.amount < 0:
                logger.warning(
                    "sell_coin_failed", user_id=user.id, symbol=coin.symbol, amount=str(amount), reason="insufficient_coins"
                )
                raise ValueError("Недостаточно монет в портфеле")

            price = get_latest_price(coin)
            cost = amount * price
            new_balance = balance.amount + cost
            balance.amount = new_balance
            balance.save()

            if portfolio.amount == 0:
                portfolio.delete()
            else:
                portfolio.save()

            transaction.on_commit(
                lambda: logger.info(
                    "sell_coin", user_id=user.id, symbol=coin.symbol, amount=str(amount), price=str(price), cost=str(cost)
                )
            )

        return {"successful": "Операция прошла успешно"}

    @staticmethod
    def get_summary(user: User) -> dict[str, Decimal | None]:
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
