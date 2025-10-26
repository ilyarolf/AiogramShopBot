#!/usr/bin/env python3
"""
KryptoExpress Payment Webhook Simulator

Simulates KryptoExpress payment webhooks for testing the payment validation system.
Includes realistic scenarios: exact payment, overpayment, underpayment, late payment.

NOTE: The bot calculates fiat amounts from crypto amounts using the invoice exchange rate.
      The --fiat-amount parameter is optional and ignored by the bot.

Usage:
    # Exact payment (using invoice number)
    python tests/manual/simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.001

    # Overpayment (10%)
    python tests/manual/simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.0011 --amount-required 0.001

    # Underpayment (90%)
    python tests/manual/simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.0009 --amount-required 0.001

    # Late payment
    python tests/manual/simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.001 --late

Requirements:
    pip install requests

Configuration:
    Set WEBHOOK_URL environment variable or use --url flag
    Auto-constructs from WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_PATH if not set
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests module not found. Install with: pip install requests")
    sys.exit(1)


class WebhookSimulator:
    """Simulates KryptoExpress payment webhooks"""

    def __init__(self, webhook_url: str, api_secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.api_secret = api_secret or os.getenv("KRYPTO_EXPRESS_API_SECRET", "")

    def create_payment_payload(
        self,
        payment_id: int,
        amount_paid: float,
        amount_required: Optional[float] = None,
        crypto: str = "BTC",
        fiat_amount: Optional[float] = None,
        is_paid: bool = True,
        tx_hash: Optional[str] = None
    ) -> dict:
        """
        Creates realistic payment webhook payload

        Args:
            payment_id: KryptoExpress payment ID
            amount_paid: Crypto amount actually paid
            amount_required: Expected crypto amount (defaults to amount_paid)
            crypto: Cryptocurrency (BTC, ETH, LTC, etc.)
            fiat_amount: Fiat equivalent (optional, defaults to dummy value)
                         NOTE: Bot ignores this and calculates from invoice rate
            is_paid: Payment status
            tx_hash: Blockchain transaction hash (auto-generated if None)

        Returns:
            dict: Webhook payload
        """
        if amount_required is None:
            amount_required = amount_paid

        if fiat_amount is None:
            # Dummy fiat amount (bot will recalculate from invoice rate anyway)
            fiat_amount = 50.0

        if tx_hash is None:
            # Generate realistic fake TX hash
            tx_hash = hashlib.sha256(
                f"{payment_id}{amount_paid}{time.time()}".encode()
            ).hexdigest()

        payload = {
            "id": payment_id,
            "address": self._generate_crypto_address(crypto),
            "cryptoAmount": amount_paid,
            "cryptoCurrency": crypto,
            "fiatAmount": fiat_amount,  # Bot recalculates this from invoice
            "fiatCurrency": "EUR",
            "isPaid": is_paid,
            "paymentType": "PAYMENT",
            "hash": tx_hash
        }

        return payload

    def _generate_crypto_address(self, crypto: str) -> str:
        """Generates realistic fake crypto address"""
        addresses = {
            "BTC": f"bc1qmock{int(time.time() * 1000) % 1000000}test",
            "ETH": f"0xMOCK{hex(int(time.time() * 1000) % 0xFFFFFFFF)[2:].upper()}TEST",
            "LTC": f"ltc1qmock{int(time.time() * 1000) % 1000000}test",
            "SOL": f"MOCK{int(time.time() * 1000) % 100000000}SOL",
        }
        return addresses.get(crypto, f"MOCK_{crypto}_{int(time.time())}")

    def calculate_hmac_signature(self, payload: dict) -> str:
        """
        Calculates HMAC-SHA512 signature for webhook

        Args:
            payload: Webhook payload

        Returns:
            str: HMAC signature (hex)
        """
        if not self.api_secret:
            print("WARNING: No API secret set - signature will be empty")
            return ""

        # Convert payload to JSON (without whitespace, like KryptoExpress does)
        payload_json = json.dumps(payload, separators=(',', ':'))
        payload_bytes = payload_json.encode('utf-8')

        # Calculate HMAC-SHA512
        secret_key = self.api_secret.encode('utf-8')
        hmac_obj = hmac.new(secret_key, payload_bytes, hashlib.sha512)
        signature = hmac_obj.hexdigest()

        return signature

    def send_webhook(self, payload: dict, include_signature: bool = True) -> dict:
        """
        Sends webhook to server

        Args:
            payload: Webhook payload
            include_signature: Whether to include X-Signature header

        Returns:
            dict: Response data
        """
        headers = {
            "Content-Type": "application/json"
        }

        if include_signature and self.api_secret:
            signature = self.calculate_hmac_signature(payload)
            headers["X-Signature"] = signature

        print(f"\n{'='*80}")
        print(f"Sending webhook to: {self.webhook_url}")
        print(f"{'='*80}")
        print(f"Payload:")
        print(json.dumps(payload, indent=2))
        print(f"\nHeaders:")
        for key, value in headers.items():
            if key == "X-Signature":
                print(f"  {key}: {value[:20]}... (truncated)")
            else:
                print(f"  {key}: {value}")
        print(f"{'='*80}\n")

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )

            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")

            return {
                "status_code": response.status_code,
                "body": response.text,
                "success": response.status_code == 200
            }

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to send webhook: {e}")
            return {
                "status_code": 0,
                "body": str(e),
                "success": False
            }


def main():
    parser = argparse.ArgumentParser(
        description="Simulate KryptoExpress payment webhooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Exact payment (0.001 BTC) - fiat calculated by bot from invoice rate
  python simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.001

  # Overpayment (10% more)
  python simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.0011 --amount-required 0.001

  # Underpayment (90%)
  python simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.0009 --amount-required 0.001

  # Late payment (payment received after deadline)
  python simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.001 --late

  # Different cryptocurrency
  python simulate_payment_webhook.py --invoice-number 2025-ABCDEF --amount-paid 0.05 --crypto ETH
        """
    )

    parser.add_argument("--payment-id", type=int, required=False,
                        help="Payment ID from KryptoExpress (auto-detected if --invoice-number provided)")
    parser.add_argument("--invoice-number", type=str, required=False,
                        help="Invoice number from bot (e.g., 2025-ABCDEF) - will lookup payment ID")
    parser.add_argument("--amount-paid", type=float, required=True,
                        help="Crypto amount actually paid")
    parser.add_argument("--amount-required", type=float, default=None,
                        help="Expected crypto amount (defaults to amount-paid)")
    parser.add_argument("--crypto", default="BTC",
                        choices=["BTC", "ETH", "LTC", "SOL", "BNB", "USDT_TRC20", "USDT_ERC20", "USDC_ERC20"],
                        help="Cryptocurrency")
    parser.add_argument("--fiat-amount", type=float, default=None,
                        help="Fiat equivalent (EUR) - IGNORED by bot (calculates from invoice rate)")
    parser.add_argument("--url", default=None,
                        help="Webhook URL (defaults to WEBHOOK_URL env var)")
    parser.add_argument("--api-secret", default=None,
                        help="API secret for HMAC signature (defaults to KRYPTO_EXPRESS_API_SECRET env var)")
    parser.add_argument("--no-signature", action="store_true",
                        help="Skip HMAC signature (for testing validation)")
    parser.add_argument("--not-paid", action="store_true",
                        help="Mark payment as not paid (isPaid=false)")
    parser.add_argument("--late", action="store_true",
                        help="Simulate late payment (add comment)")
    parser.add_argument("--tx-hash", default=None,
                        help="Custom transaction hash")

    args = parser.parse_args()

    # Validate: Either payment-id OR invoice-number must be provided
    if not args.payment_id and not args.invoice_number:
        print("ERROR: Either --payment-id or --invoice-number must be provided.")
        sys.exit(1)

    # If invoice-number provided, lookup payment-id from database
    if args.invoice_number and not args.payment_id:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), '../../data/database.db')
        if not os.path.exists(db_path):
            print(f"ERROR: Database not found at {db_path}")
            sys.exit(1)

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # First, check if there are ANY invoices
            cursor.execute("SELECT COUNT(*) FROM invoices")
            total_invoices = cursor.fetchone()[0]

            cursor.execute("SELECT payment_processing_id FROM invoices WHERE invoice_number = ?", (args.invoice_number,))
            result = cursor.fetchone()

            if not result:
                print(f"ERROR: No invoice found with number '{args.invoice_number}'")
                print(f"\nℹ️  Database has {total_invoices} invoices total.")
                if total_invoices > 0:
                    cursor.execute("SELECT invoice_number FROM invoices ORDER BY id DESC LIMIT 5")
                    recent = cursor.fetchall()
                    print(f"   Recent invoices:")
                    for inv in recent:
                        print(f"     - {inv[0]}")
                conn.close()
                sys.exit(1)

            args.payment_id = result[0]
            print(f"✓ Looked up payment ID: {args.payment_id} for invoice {args.invoice_number}")
            conn.close()
        except Exception as e:
            print(f"ERROR: Database lookup failed: {e}")
            sys.exit(1)

    # Get webhook URL
    webhook_url = args.url or os.getenv("WEBHOOK_URL")

    # If no explicit URL provided, construct from .env variables
    if not webhook_url:
        webapp_host = os.getenv("WEBAPP_HOST", "localhost")
        webapp_port = os.getenv("WEBAPP_PORT", "5001")
        webhook_path = os.getenv("WEBHOOK_PATH", "/")
        # Remove trailing slash from webhook_path to avoid double slashes
        webhook_path = webhook_path.rstrip("/")
        webhook_url = f"http://{webapp_host}:{webapp_port}{webhook_path}/cryptoprocessing/event"
        print(f"ℹ️  No WEBHOOK_URL set, using constructed URL: {webhook_url}")
        print(f"   (from WEBAPP_HOST={webapp_host}, WEBAPP_PORT={webapp_port}, WEBHOOK_PATH={webhook_path})")
        print()

    # Initialize simulator
    simulator = WebhookSimulator(
        webhook_url=webhook_url,
        api_secret=args.api_secret
    )

    # Create payload
    payload = simulator.create_payment_payload(
        payment_id=args.payment_id,
        amount_paid=args.amount_paid,
        amount_required=args.amount_required,
        crypto=args.crypto,
        fiat_amount=args.fiat_amount,
        is_paid=not args.not_paid,
        tx_hash=args.tx_hash
    )

    # Add scenario info
    if args.late:
        print("\n⏰ SCENARIO: Late Payment (received after deadline)")
    elif args.amount_required and args.amount_paid < args.amount_required:
        shortfall = args.amount_required - args.amount_paid
        percent = (shortfall / args.amount_required) * 100
        print(f"\n⚠️  SCENARIO: Underpayment ({percent:.1f}% short)")
    elif args.amount_required and args.amount_paid > args.amount_required:
        excess = args.amount_paid - args.amount_required
        percent = (excess / args.amount_required) * 100
        print(f"\n💰 SCENARIO: Overpayment (+{percent:.1f}% excess)")
    else:
        print("\n✅ SCENARIO: Exact Payment")

    # Send webhook
    result = simulator.send_webhook(
        payload=payload,
        include_signature=not args.no_signature
    )

    # Exit code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
