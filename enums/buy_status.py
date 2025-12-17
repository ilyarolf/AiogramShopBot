from enum import Enum


class BuyStatus(Enum):
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"
