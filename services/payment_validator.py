"""
Payment Validator Service

Validates incoming payment amounts against order requirements.
Implements the payment validation rules from Terms & Conditions:

- ZERO tolerance for underpayment
- 0.1% tolerance for overpayment (forfeits to shop)
- >0.1% overpayment goes to wallet
- Currency mismatch detection
- Late payment detection
"""

from datetime import datetime
from typing import Tuple

import config
from enums.cryptocurrency import Cryptocurrency
from enums.payment_validation import PaymentValidationResult


class PaymentValidator:
    """
    Validates payment amounts and classifies payment types.

    Usage:
        result = PaymentValidator.validate_payment(
            paid=0.00095,
            required=0.001,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=datetime(2025, 10, 20, 10, 15)
        )

        if result == PaymentValidationResult.EXACT_MATCH:
            # Complete order
        elif result == PaymentValidationResult.UNDERPAYMENT:
            # Handle underpayment
        # ... etc
    """

    @staticmethod
    def validate_payment(
        paid: float,
        required: float,
        currency_paid: Cryptocurrency,
        currency_required: Cryptocurrency,
        deadline: datetime,
        tolerance_percent: float = None
    ) -> PaymentValidationResult:
        """
        Validates payment amount and returns classification.

        Args:
            paid: Amount actually paid (crypto)
            required: Amount that should be paid (crypto)
            currency_paid: Cryptocurrency used for payment
            currency_required: Cryptocurrency expected
            deadline: Order expiration deadline
            tolerance_percent: Overpayment tolerance % (default from config)

        Returns:
            PaymentValidationResult enum indicating payment classification

        Examples:
            >>> validate_payment(0.001, 0.001, BTC, BTC, deadline)
            PaymentValidationResult.EXACT_MATCH

            >>> validate_payment(0.00099, 0.001, BTC, BTC, deadline)
            PaymentValidationResult.UNDERPAYMENT

            >>> validate_payment(0.00101, 0.001, BTC, BTC, deadline)
            PaymentValidationResult.OVERPAYMENT
        """

        # Use config default if tolerance not specified
        if tolerance_percent is None:
            tolerance_percent = config.PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT

        # 1. Check currency mismatch
        if currency_paid != currency_required:
            return PaymentValidationResult.CURRENCY_MISMATCH

        # 2. Check if payment is late
        if datetime.now() > deadline:
            return PaymentValidationResult.LATE_PAYMENT

        # 3. Check for underpayment (ZERO tolerance!)
        if paid < required:
            return PaymentValidationResult.UNDERPAYMENT

        # 4. Calculate overpayment tolerance threshold
        tolerance_multiplier = 1 + (tolerance_percent / 100)
        tolerance_threshold = required * tolerance_multiplier

        # 5. Check for exact match
        if paid == required:
            return PaymentValidationResult.EXACT_MATCH

        # 6. Check for minor overpayment (within tolerance)
        if paid <= tolerance_threshold:
            return PaymentValidationResult.MINOR_OVERPAYMENT

        # 7. Significant overpayment (above tolerance)
        return PaymentValidationResult.OVERPAYMENT

    @staticmethod
    def calculate_overpayment_amount(paid: float, required: float) -> float:
        """
        Calculates overpayment amount (excess above required).

        Args:
            paid: Amount actually paid
            required: Amount that should be paid

        Returns:
            Overpayment amount (0 if no overpayment)

        Example:
            >>> calculate_overpayment_amount(0.00105, 0.001)
            0.00005
        """
        return max(0.0, paid - required)

    @staticmethod
    def calculate_underpayment_amount(paid: float, required: float) -> float:
        """
        Calculates underpayment amount (shortfall below required).

        Args:
            paid: Amount actually paid
            required: Amount that should be paid

        Returns:
            Underpayment amount (0 if no underpayment)

        Example:
            >>> calculate_underpayment_amount(0.00095, 0.001)
            0.00005
        """
        return max(0.0, required - paid)

    @staticmethod
    def calculate_penalty(amount: float, penalty_percent: float = None) -> Tuple[float, float]:
        """
        Calculates penalty fee and net amount after penalty.

        IMPORTANT: Penalty is always rounded DOWN (floor) to 2 decimals to favor the customer.
        This prevents rounding errors that disadvantage the user.

        Args:
            amount: Original amount
            penalty_percent: Penalty percentage (default from config)

        Returns:
            Tuple of (penalty_amount, net_amount_after_penalty)

        Example:
            >>> calculate_penalty(18.91, 5.0)
            (0.94, 17.97)  # 5% of 18.91 = 0.9455 → rounded DOWN to 0.94

            >>> calculate_penalty(50.0, 5.0)
            (2.50, 47.50)  # 5% of €50 = €2.50 penalty
        """
        from decimal import Decimal, ROUND_DOWN

        if penalty_percent is None:
            penalty_percent = config.PAYMENT_UNDERPAYMENT_PENALTY_PERCENT

        # Use Decimal for precise money calculations
        amount_decimal = Decimal(str(amount))
        penalty_percent_decimal = Decimal(str(penalty_percent))

        # Calculate penalty and round DOWN (floor) to favor customer
        penalty_amount_decimal = (amount_decimal * penalty_percent_decimal / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_DOWN
        )

        # Net amount is exact subtraction (no additional rounding)
        net_amount_decimal = amount_decimal - penalty_amount_decimal

        # Convert back to float
        penalty_amount = float(penalty_amount_decimal)
        net_amount = float(net_amount_decimal)

        return penalty_amount, net_amount

    @staticmethod
    def should_forfeit_overpayment(paid: float, required: float, tolerance_percent: float = None) -> bool:
        """
        Determines if overpayment should be forfeited to shop (vs. credited to wallet).

        Args:
            paid: Amount actually paid
            required: Amount that should be paid
            tolerance_percent: Overpayment tolerance % (default from config)

        Returns:
            True if overpayment should forfeit, False if should credit to wallet

        Example:
            >>> should_forfeit_overpayment(0.00100050, 0.001)  # +0.05%
            True  # Minor overpayment, forfeits to shop

            >>> should_forfeit_overpayment(0.0011, 0.001)  # +10%
            False  # Significant overpayment, goes to wallet
        """
        if tolerance_percent is None:
            tolerance_percent = config.PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT

        result = PaymentValidator.validate_payment(
            paid=paid,
            required=required,
            currency_paid=Cryptocurrency.BTC,  # Dummy, only amount matters here
            currency_required=Cryptocurrency.BTC,
            deadline=datetime.now() + timedelta(minutes=1),  # Dummy future deadline
            tolerance_percent=tolerance_percent
        )

        return result == PaymentValidationResult.MINOR_OVERPAYMENT

    @staticmethod
    def format_validation_result_message(
        result: PaymentValidationResult,
        paid: float,
        required: float,
        currency: Cryptocurrency
    ) -> str:
        """
        Formats a human-readable message for validation result.

        Args:
            result: Validation result
            paid: Amount paid
            required: Amount required
            currency: Cryptocurrency

        Returns:
            Human-readable message string

        Example:
            >>> format_validation_result_message(
            ...     PaymentValidationResult.UNDERPAYMENT,
            ...     0.00095,
            ...     0.001,
            ...     Cryptocurrency.BTC
            ... )
            "Underpayment: Paid 0.00095 BTC, required 0.001 BTC (missing 0.00005 BTC)"
        """
        messages = {
            PaymentValidationResult.EXACT_MATCH: (
                f"Exact match: Paid {paid} {currency.value}, required {required} {currency.value}"
            ),
            PaymentValidationResult.MINOR_OVERPAYMENT: (
                f"Minor overpayment: Paid {paid} {currency.value}, required {required} {currency.value} "
                f"(excess {paid - required} {currency.value} forfeits to shop)"
            ),
            PaymentValidationResult.OVERPAYMENT: (
                f"Overpayment: Paid {paid} {currency.value}, required {required} {currency.value} "
                f"(excess {paid - required} {currency.value} credited to wallet)"
            ),
            PaymentValidationResult.UNDERPAYMENT: (
                f"Underpayment: Paid {paid} {currency.value}, required {required} {currency.value} "
                f"(missing {required - paid} {currency.value})"
            ),
            PaymentValidationResult.LATE_PAYMENT: (
                f"Late payment: Paid {paid} {currency.value} after deadline (5% penalty applied)"
            ),
            PaymentValidationResult.CURRENCY_MISMATCH: (
                f"Currency mismatch: Cannot process payment"
            ),
        }

        return messages.get(result, f"Unknown validation result: {result}")


# Import needed for should_forfeit_overpayment
from datetime import timedelta
