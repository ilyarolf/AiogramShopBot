"""
Test for Payment Validation System

Tests the payment amount validation logic including:
- Exact payment detection
- Overpayment handling (minor vs significant)
- Underpayment detection (zero tolerance)
- Late payment handling
- Currency mismatch detection

Run with:
    pytest tests/test_payment_validation.py -v
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from services.payment_validator import PaymentValidator
from enums.payment_validation import PaymentValidationResult
from enums.cryptocurrency import Cryptocurrency
import config


class TestPaymentValidation:
    """
    Test suite for payment validation logic.

    These tests verify the core payment validation rules:
    - ZERO tolerance for underpayment
    - 0.1% tolerance for overpayment (forfeits to shop)
    - >0.1% overpayment goes to wallet
    """

    def test_exact_payment_is_accepted(self):
        """
        Test that exact payment amount is accepted.

        Expected: PaymentValidationResult.EXACT_MATCH
        """
        required = 0.001
        paid = 0.001
        deadline = datetime.now() + timedelta(minutes=15)

        result = PaymentValidator.validate_payment(
            paid=paid,
            required=required,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )

        assert result == PaymentValidationResult.EXACT_MATCH

    def test_minor_overpayment_within_tolerance_is_accepted(self):
        """
        Test that overpayment ≤0.1% is accepted as exact (forfeits to shop).

        Example:
        - Required: 0.00100000 BTC
        - Paid: 0.00100050 BTC (+0.05%)
        - Result: MINOR_OVERPAYMENT (forfeits to shop, no wallet credit)

        Expected: PaymentValidationResult.MINOR_OVERPAYMENT
        """
        deadline = datetime.now() + timedelta(minutes=15)

        # Test case 1: +0.01% overpayment
        result1 = PaymentValidator.validate_payment(
            paid=1.0001,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result1 == PaymentValidationResult.MINOR_OVERPAYMENT

        # Test case 2: +0.1% overpayment (edge case - exactly at tolerance)
        result2 = PaymentValidator.validate_payment(
            paid=1.001,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result2 == PaymentValidationResult.MINOR_OVERPAYMENT

        # Test case 3: +0.05% overpayment
        result3 = PaymentValidator.validate_payment(
            paid=100.05,
            required=100.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result3 == PaymentValidationResult.MINOR_OVERPAYMENT

    def test_significant_overpayment_goes_to_wallet(self):
        """
        Test that overpayment >0.1% is credited to wallet.

        Example:
        - Required: €10.00
        - Paid: €10.50 (+5%)
        - Result: OVERPAYMENT (€0.50 to wallet)

        Expected: PaymentValidationResult.OVERPAYMENT
        """
        deadline = datetime.now() + timedelta(minutes=15)

        # Test case 1: +0.2% overpayment (just above tolerance)
        result1 = PaymentValidator.validate_payment(
            paid=10.02,
            required=10.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result1 == PaymentValidationResult.OVERPAYMENT

        # Test case 2: +50% overpayment
        result2 = PaymentValidator.validate_payment(
            paid=15.0,
            required=10.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result2 == PaymentValidationResult.OVERPAYMENT

        # Test case 3: +100% overpayment
        result3 = PaymentValidator.validate_payment(
            paid=0.002,
            required=0.001,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result3 == PaymentValidationResult.OVERPAYMENT

    def test_underpayment_zero_tolerance(self):
        """
        Test that ANY underpayment is rejected (zero tolerance).

        Example:
        - Required: 0.001 BTC
        - Paid: 0.00099999 BTC (-0.001%)
        - Result: UNDERPAYMENT

        Expected: PaymentValidationResult.UNDERPAYMENT
        """
        deadline = datetime.now() + timedelta(minutes=15)

        # Test case 1: -0.001% underpayment (tiny!)
        result1 = PaymentValidator.validate_payment(
            paid=0.99999,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result1 == PaymentValidationResult.UNDERPAYMENT

        # Test case 2: -0.1% underpayment
        result2 = PaymentValidator.validate_payment(
            paid=0.999,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result2 == PaymentValidationResult.UNDERPAYMENT

        # Test case 3: -50% underpayment
        result3 = PaymentValidator.validate_payment(
            paid=0.5,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result3 == PaymentValidationResult.UNDERPAYMENT

        # Test case 4: No payment at all
        result4 = PaymentValidator.validate_payment(
            paid=0.0,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result4 == PaymentValidationResult.UNDERPAYMENT

    def test_currency_mismatch_detection(self):
        """
        Test that wrong cryptocurrency is detected.

        Example:
        - Required: BTC
        - Paid: LTC
        - Result: CURRENCY_MISMATCH

        Expected: PaymentValidationResult.CURRENCY_MISMATCH
        """
        deadline = datetime.now() + timedelta(minutes=15)

        # Test case 1: BTC required, LTC paid
        result1 = PaymentValidator.validate_payment(
            paid=1.0,
            required=1.0,
            currency_paid=Cryptocurrency.LTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result1 == PaymentValidationResult.CURRENCY_MISMATCH

        # Test case 2: BTC required, ETH paid
        result2 = PaymentValidator.validate_payment(
            paid=1.0,
            required=1.0,
            currency_paid=Cryptocurrency.ETH,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result2 == PaymentValidationResult.CURRENCY_MISMATCH

    def test_late_payment_detection(self):
        """
        Test that payment after deadline is marked as late.

        Example:
        - Order expires_at: 10:15
        - Payment received_at: 10:20
        - Result: LATE_PAYMENT (5% penalty applied)

        Expected: PaymentValidationResult.LATE_PAYMENT
        """
        # Test case 1: Payment 1 second after deadline
        deadline = datetime.now() - timedelta(seconds=1)
        result1 = PaymentValidator.validate_payment(
            paid=1.0,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result1 == PaymentValidationResult.LATE_PAYMENT

        # Test case 2: Payment 5 minutes after deadline
        deadline = datetime.now() - timedelta(minutes=5)
        result2 = PaymentValidator.validate_payment(
            paid=1.0,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result2 == PaymentValidationResult.LATE_PAYMENT

        # Test case 3: Payment 1 second before deadline (should not be late)
        deadline = datetime.now() + timedelta(seconds=1)
        result3 = PaymentValidator.validate_payment(
            paid=1.0,
            required=1.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result3 == PaymentValidationResult.EXACT_MATCH  # Not late!

    def test_overpayment_tolerance_is_configurable(self):
        """
        Test that overpayment tolerance respects config.

        Default: 0.1%
        Custom: Could be changed to 0.5% or 1.0%

        Expected: Tolerance threshold adjusts based on config
        """
        deadline = datetime.now() + timedelta(minutes=15)

        # Test with custom tolerance of 0.5% (paid 100.3 = 0.3% over, within tolerance)
        result1 = PaymentValidator.validate_payment(
            paid=100.3,
            required=100.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline,
            tolerance_percent=0.5  # Custom: 0.5%
        )
        assert result1 == PaymentValidationResult.MINOR_OVERPAYMENT

        # Test with custom tolerance of 1.0%
        result2 = PaymentValidator.validate_payment(
            paid=101.0,
            required=100.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline,
            tolerance_percent=1.0  # Custom: 1.0%
        )
        assert result2 == PaymentValidationResult.MINOR_OVERPAYMENT

        # Test above custom tolerance (1.1% with 1.0% tolerance)
        result3 = PaymentValidator.validate_payment(
            paid=101.1,
            required=100.0,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline,
            tolerance_percent=1.0  # Custom: 1.0%
        )
        assert result3 == PaymentValidationResult.OVERPAYMENT

    def test_floating_point_precision_edge_cases(self):
        """
        Test that floating point precision doesn't cause false positives.

        Example:
        - 0.1 + 0.2 = 0.30000000000000004 (floating point issue)
        - Should still be treated as exact match

        Expected: Proper decimal handling
        """
        deadline = datetime.now() + timedelta(minutes=15)

        # Test case 1: Classic floating point issue (0.1 + 0.2)
        # Note: Python's float arithmetic means 0.1 + 0.2 != 0.3
        # But our validator should handle this gracefully
        paid = 0.1 + 0.2  # = 0.30000000000000004
        required = 0.3

        result1 = PaymentValidator.validate_payment(
            paid=paid,
            required=required,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        # Should be within tolerance (tiny difference)
        assert result1 in [PaymentValidationResult.EXACT_MATCH, PaymentValidationResult.MINOR_OVERPAYMENT]

        # Test case 2: Very small amounts (satoshi-level precision)
        result2 = PaymentValidator.validate_payment(
            paid=0.00000001,  # 1 satoshi
            required=0.00000001,
            currency_paid=Cryptocurrency.BTC,
            currency_required=Cryptocurrency.BTC,
            deadline=deadline
        )
        assert result2 == PaymentValidationResult.EXACT_MATCH


class TestPaymentValidatorHelpers:
    """
    Test suite for PaymentValidator helper methods.
    """

    def test_calculate_overpayment_amount(self):
        """Test overpayment amount calculation."""
        assert abs(PaymentValidator.calculate_overpayment_amount(1.05, 1.0) - 0.05) < 0.0001
        assert PaymentValidator.calculate_overpayment_amount(1.0, 1.0) == 0.0
        assert PaymentValidator.calculate_overpayment_amount(0.95, 1.0) == 0.0  # No overpayment

    def test_calculate_underpayment_amount(self):
        """Test underpayment amount calculation."""
        assert abs(PaymentValidator.calculate_underpayment_amount(0.95, 1.0) - 0.05) < 0.0001
        assert PaymentValidator.calculate_underpayment_amount(1.0, 1.0) == 0.0
        assert PaymentValidator.calculate_underpayment_amount(1.05, 1.0) == 0.0  # No underpayment

    def test_calculate_penalty(self):
        """Test penalty calculation."""
        penalty, net = PaymentValidator.calculate_penalty(100.0, 5.0)
        assert penalty == 5.0
        assert net == 95.0

        penalty, net = PaymentValidator.calculate_penalty(50.0, 5.0)
        assert penalty == 2.5
        assert net == 47.5

    def test_should_forfeit_overpayment(self):
        """Test forfeit determination."""
        # Minor overpayment should forfeit
        assert PaymentValidator.should_forfeit_overpayment(1.0005, 1.0, tolerance_percent=0.1) == True

        # Significant overpayment should not forfeit (goes to wallet)
        assert PaymentValidator.should_forfeit_overpayment(1.05, 1.0, tolerance_percent=0.1) == False

    def test_format_validation_result_message(self):
        """Test validation result message formatting."""
        msg = PaymentValidator.format_validation_result_message(
            PaymentValidationResult.EXACT_MATCH,
            0.001,
            0.001,
            Cryptocurrency.BTC
        )
        assert "Exact match" in msg
        assert "0.001" in msg
        assert "BTC" in msg


# Manual test runner
if __name__ == "__main__":
    """
    Run tests manually without pytest.

    Usage:
        python tests/test_payment_validation.py
    """
    import sys

    print("=" * 80)
    print("Payment Validation System - Tests Implemented")
    print("=" * 80)
    print()
    print("✅ Tests are now implemented and ready to run!")
    print()
    print("To run with pytest:")
    print("    pytest tests/test_payment_validation.py -v")
    print()
    print("To run with coverage:")
    print("    pytest tests/test_payment_validation.py --cov=services.payment_validator -v")
    print()
    print("=" * 80)

    sys.exit(0)
