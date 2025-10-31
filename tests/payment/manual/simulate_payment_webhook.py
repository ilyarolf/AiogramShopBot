#!/usr/bin/env python3
"""
KryptoExpress Payment Webhook Simulator

Simulates KryptoExpress payment webhooks for testing the payment validation system.
Includes realistic scenarios: exact payment, overpayment, underpayment, late payment.

NOTE: The bot calculates fiat amounts from crypto amounts using the invoice exchange rate.
      The --fiat-amount parameter is optional and ignored by the bot.

Usage:
    # Order payment - exact amount (currency auto-detected from invoice)
    python tests/manual/simulate_payment_webhook.py --reference INV-2025-ABCDEF --amount-paid 0.001

    # Order payment - underpayment
    python tests/manual/simulate_payment_webhook.py --reference INV-2025-ABCDEF --amount-paid 0.0009

    # Top-up deposit (defaults to BTC)
    python tests/manual/simulate_payment_webhook.py --reference TOPUP-2025-ABCDEF --amount-paid 0.001

    # Late payment
    python tests/manual/simulate_payment_webhook.py --reference INV-2025-ABCDEF --amount-paid 0.001 --late

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
        crypto: str = "BTC",
        is_paid: bool = True,
        tx_hash: Optional[str] = None,
        payment_type: str = "PAYMENT"
    ) -> dict:
        """
        Creates realistic KryptoExpress webhook payload

        Simulates exactly what KryptoExpress sends to our webhook endpoint.
        The bot will look up expected amounts from the database internally.

        Args:
            payment_id: KryptoExpress payment ID
            amount_paid: Crypto amount actually paid
            crypto: Cryptocurrency (BTC, ETH, LTC, etc.)
            is_paid: Payment status
            tx_hash: Blockchain transaction hash (auto-generated if None)
            payment_type: "PAYMENT" (order) or "DEPOSIT" (top-up)

        Returns:
            dict: Webhook payload matching KryptoExpress format
        """
        if tx_hash is None:
            # Generate realistic fake TX hash
            tx_hash = hashlib.sha256(
                f"{payment_id}{amount_paid}{time.time()}".encode()
            ).hexdigest()

        # Dummy fiat amount - bot ignores this and calculates from invoice
        fiat_amount = 50.0

        payload = {
            "id": payment_id,
            "address": self._generate_crypto_address(crypto),
            "cryptoAmount": amount_paid,
            "cryptoCurrency": crypto,
            "fiatAmount": fiat_amount,
            "fiatCurrency": "EUR",
            "isPaid": is_paid,
            "paymentType": payment_type,
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
  # Order payment - exact amount
  python simulate_payment_webhook.py --reference INV-2025-ABCDEF --amount-paid 0.001

  # Order payment - underpayment (90%)
  python simulate_payment_webhook.py --reference INV-2025-ABCDEF --amount-paid 0.0009

  # Order payment - overpayment (110%)
  python simulate_payment_webhook.py --reference INV-2025-ABCDEF --amount-paid 0.0011

  # Deposit (top-up, defaults to BTC)
  python simulate_payment_webhook.py --reference TOPUP-2025-ABCDEF --amount-paid 0.001

  # Test webhook without signature (security testing)
  python simulate_payment_webhook.py --reference INV-2025-ABCDEF --amount-paid 0.001 --no-signature
        """
    )

    parser.add_argument("--reference", type=str, required=True,
                        help="Payment reference: INV-YYYY-ABCDEF (order) or TOPUP-YYYY-ABCDEF (deposit)")
    parser.add_argument("--amount-paid", type=float, required=True,
                        help="Crypto amount actually paid (simulates what KryptoExpress sends)")
    parser.add_argument("--no-signature", action="store_true",
                        help="Skip HMAC signature (for testing security validation)")

    args = parser.parse_args()

    # Detect payment type from reference prefix
    reference = args.reference.upper()

    if reference.startswith("INV-"):
        payment_type = "PAYMENT"
        print(f"📄 Detected ORDER payment from reference: {reference}")
    elif reference.startswith("TOPUP-"):
        payment_type = "DEPOSIT"
        print(f"💰 Detected DEPOSIT from reference: {reference}")
    else:
        print(f"ERROR: Invalid reference format: {args.reference}")
        print("       Must start with INV- (order) or TOPUP- (deposit)")
        print("       Examples: INV-2025-ABCDEF, TOPUP-2025-ABCDEF")
        sys.exit(1)

    # Lookup payment_id from database
    payment_id = None

    if payment_type == "PAYMENT":
        # Lookup order invoice
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), '../../../data/database.db')
        if not os.path.exists(db_path):
            print(f"ERROR: Database not found at {db_path}")
            sys.exit(1)

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT payment_processing_id, payment_amount_crypto, payment_crypto_currency
                FROM invoices
                WHERE invoice_number = ?
            """, (reference,))
            result = cursor.fetchone()

            if not result:
                cursor.execute("SELECT COUNT(*) FROM invoices")
                total = cursor.fetchone()[0]
                print(f"ERROR: Invoice not found: {reference}")
                print(f"ℹ️  Database has {total} invoices. Recent:")
                cursor.execute("SELECT invoice_number FROM invoices ORDER BY id DESC LIMIT 5")
                for inv in cursor.fetchall():
                    print(f"     - {inv[0]}")
                conn.close()
                sys.exit(1)

            payment_id = result[0]
            expected_amount = result[1]
            expected_currency = result[2]

            # Use invoice currency (auto-detected)
            crypto = expected_currency
            print(f"  Payment ID: {payment_id}")
            print(f"  Expected: {expected_amount} {expected_currency}")
            print(f"  Testing: {args.amount_paid} {crypto} (from invoice)")

            conn.close()
        except Exception as e:
            print(f"ERROR: Database lookup failed: {e}")
            sys.exit(1)

    elif payment_type == "DEPOSIT":
        # Lookup deposit/top-up
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), '../../../data/database.db')
        if not os.path.exists(db_path):
            print(f"ERROR: Database not found at {db_path}")
            sys.exit(1)

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT processing_payment_id FROM payments WHERE topup_reference = ?", (reference,))
            result = cursor.fetchone()

            if not result:
                print(f"ERROR: Deposit not found: {reference}")
                cursor.execute("SELECT topup_reference FROM payments WHERE topup_reference IS NOT NULL ORDER BY id DESC LIMIT 5")
                recent = cursor.fetchall()
                if recent:
                    print(f"ℹ️  Recent deposits:")
                    for ref in recent:
                        print(f"     - {ref[0]}")
                conn.close()
                sys.exit(1)

            payment_id = result[0]

            # Default to BTC for deposits
            crypto = "BTC"
            print(f"  Payment ID: {payment_id}")
            print(f"  Testing: {args.amount_paid} {crypto} (default)")

            conn.close()
        except Exception as e:
            print(f"ERROR: Database lookup failed: {e}")
            sys.exit(1)

    # Get webhook URL from environment
    webhook_url = os.getenv("WEBHOOK_URL")

    # If not set, construct from .env variables
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

    # Initialize simulator (api_secret from environment)
    simulator = WebhookSimulator(
        webhook_url=webhook_url,
        api_secret=None  # Uses KRYPTO_EXPRESS_API_SECRET from env
    )

    # Create payload (simulates what KryptoExpress sends)
    payload = simulator.create_payment_payload(
        payment_id=payment_id,
        amount_paid=args.amount_paid,
        crypto=crypto,
        is_paid=True,  # Always simulate successful payment
        tx_hash=None,  # Auto-generated
        payment_type=payment_type
    )

    # Print scenario info
    print(f"\n📤 Simulating KryptoExpress webhook...")
    print(f"   Payment ID: {payment_id}")
    print(f"   Amount: {args.amount_paid} {crypto}")
    print(f"   Type: {payment_type}")

    # Send webhook
    result = simulator.send_webhook(
        payload=payload,
        include_signature=not args.no_signature
    )

    # Exit code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
