from enum import Enum


class StrikeType(Enum):
    TIMEOUT = "TIMEOUT"  # Automatischer Timeout einer Order
    LATE_CANCEL = "LATE_CANCEL"  # Verspätete Stornierung durch User (nach Grace Period)