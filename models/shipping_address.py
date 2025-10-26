from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship

from models.base import Base


class ShippingAddress(Base):
    """
    Stores encrypted shipping addresses for orders with physical items.
    Address is encrypted with AES-256-GCM using order-specific secret.
    """
    __tablename__ = 'shipping_addresses'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, unique=True)

    # Encrypted address data
    encrypted_address = Column(LargeBinary, nullable=False)  # AES-256-GCM encrypted
    nonce = Column(LargeBinary, nullable=False)  # GCM nonce (12 bytes)
    tag = Column(LargeBinary, nullable=False)  # GCM authentication tag (16 bytes)

    # Relation
    order = relationship('Order', back_populates='shipping_address')
