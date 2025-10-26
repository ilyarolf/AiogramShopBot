from enum import Enum


class OrderCancelReason(Enum):
    """Reasons for order cancellation"""
    USER = "USER"               # User cancelled manually
    TIMEOUT = "TIMEOUT"         # Payment timeout expired
    ADMIN = "ADMIN"             # Admin cancelled (future feature)
