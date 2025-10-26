from enum import Enum


class OrderStatus(Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"                           # Waiting for payment (invoice created)
    PENDING_PAYMENT_AND_ADDRESS = "PENDING_PAYMENT_AND_ADDRESS"   # Physical items: waiting for shipping address
    PENDING_PAYMENT_PARTIAL = "PENDING_PAYMENT_PARTIAL"           # After 1st underpayment (30 min extension)
    PAID = "PAID"                                                 # Paid successfully (digital items only)
    PAID_AWAITING_SHIPMENT = "PAID_AWAITING_SHIPMENT"           # Paid, physical items awaiting shipment
    SHIPPED = "SHIPPED"                                           # Shipped (physical items)
    CANCELLED_BY_USER = "CANCELLED_BY_USER"                       # Cancelled by user (after grace period → strike!)
    CANCELLED_BY_ADMIN = "CANCELLED_BY_ADMIN"                     # Cancelled by admin (no strike)
    CANCELLED_BY_SYSTEM = "CANCELLED_BY_SYSTEM"                   # Auto-cancelled by system (e.g., all items out of stock)
    TIMEOUT = "TIMEOUT"                                           # Timeout expired (includes underpayment failures)