from enum import Enum


class PaymentValidationResult(Enum):
    """
    Result of payment amount validation.

    Used by PaymentValidator to classify incoming payments.
    """

    EXACT_MATCH = "EXACT_MATCH"
    # Paid exactly the required amount (within 0.1% overpayment tolerance)
    # Action: Complete order normally

    MINOR_OVERPAYMENT = "MINOR_OVERPAYMENT"
    # Paid ≤0.1% more than required
    # Action: Complete order, forfeit excess to shop (no wallet credit)

    OVERPAYMENT = "OVERPAYMENT"
    # Paid >0.1% more than required
    # Action: Complete order, credit excess to wallet

    UNDERPAYMENT = "UNDERPAYMENT"
    # Paid less than required (ANY amount below)
    # Action: 1st attempt → extend deadline + new invoice, 2nd attempt → cancel + penalty

    LATE_PAYMENT = "LATE_PAYMENT"
    # Payment received after deadline expired
    # Action: Credit to wallet with 5% penalty

    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    # Paid with wrong cryptocurrency
    # Action: Cannot be processed automatically (manual intervention required)
