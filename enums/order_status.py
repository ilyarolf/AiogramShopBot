from enum import Enum


class OrderStatus(Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"  # Wartet auf Zahlung
    PAID = "PAID"                        # Bezahlt
    SHIPPED = "SHIPPED"                  # Versendet (optional für Admin)
    CANCELLED = "CANCELLED"              # Manuell storniert (kein Strike)
    TIMEOUT = "TIMEOUT"                  # Automatisch storniert (Strike!)