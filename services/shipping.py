"""
Shipping Service

Handles shipping address encryption, storage, and retrieval for orders with physical items.
Uses AES-256-GCM encryption with PBKDF2 key derivation.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select

import config
from db import session_execute, session_commit
from models.shipping_address import ShippingAddress


class ShippingService:

    @staticmethod
    def _derive_key(order_id: int) -> bytes:
        """
        Derive encryption key from master secret + order_id using PBKDF2.

        Args:
            order_id: Order ID used as salt component

        Returns:
            32-byte encryption key
        """
        # Use order_id as part of salt for order-specific keys
        salt = config.SHIPPING_ADDRESS_SECRET.encode() + str(order_id).encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(config.SHIPPING_ADDRESS_SECRET.encode())

    @staticmethod
    def encrypt_address(plaintext_address: str, order_id: int) -> tuple[bytes, bytes, bytes]:
        """
        Encrypt shipping address using AES-256-GCM.

        Args:
            plaintext_address: Plain text shipping address
            order_id: Order ID for key derivation

        Returns:
            (encrypted_data, nonce, tag)
        """
        key = ShippingService._derive_key(order_id)
        aesgcm = AESGCM(key)

        nonce = os.urandom(12)  # 96-bit nonce for GCM
        plaintext_bytes = plaintext_address.encode('utf-8')

        # GCM mode returns ciphertext + tag concatenated
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext_bytes, None)

        # Split ciphertext and tag (last 16 bytes are tag)
        ciphertext = ciphertext_with_tag[:-16]
        tag = ciphertext_with_tag[-16:]

        return ciphertext, nonce, tag

    @staticmethod
    def decrypt_address(encrypted_address: bytes, nonce: bytes, tag: bytes, order_id: int) -> str:
        """
        Decrypt shipping address using AES-256-GCM.

        Args:
            encrypted_address: Encrypted address data
            nonce: GCM nonce
            tag: GCM authentication tag
            order_id: Order ID for key derivation

        Returns:
            Decrypted plain text address
        """
        key = ShippingService._derive_key(order_id)
        aesgcm = AESGCM(key)

        # Concatenate ciphertext and tag for GCM decryption
        ciphertext_with_tag = encrypted_address + tag

        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext_bytes.decode('utf-8')

    @staticmethod
    async def save_shipping_address(
        order_id: int,
        plaintext_address: str,
        session: AsyncSession | Session
    ):
        """
        Encrypt and save shipping address for an order.

        Args:
            order_id: Order ID
            plaintext_address: Plain text shipping address
            session: Database session
        """
        # Encrypt address
        encrypted, nonce, tag = ShippingService.encrypt_address(plaintext_address, order_id)

        # Save to database
        shipping_address = ShippingAddress(
            order_id=order_id,
            encrypted_address=encrypted,
            nonce=nonce,
            tag=tag
        )
        session.add(shipping_address)
        await session_commit(session)

    @staticmethod
    async def get_shipping_address(
        order_id: int,
        session: AsyncSession | Session
    ) -> str | None:
        """
        Retrieve and decrypt shipping address for an order.

        Args:
            order_id: Order ID
            session: Database session

        Returns:
            Decrypted plain text address or None if not found
        """
        stmt = select(ShippingAddress).where(ShippingAddress.order_id == order_id)
        result = await session_execute(stmt, session)
        shipping_address = result.scalar_one_or_none()

        if not shipping_address:
            return None

        # Decrypt and return
        return ShippingService.decrypt_address(
            shipping_address.encrypted_address,
            shipping_address.nonce,
            shipping_address.tag,
            order_id
        )

    @staticmethod
    async def delete_shipping_address(
        order_id: int,
        session: AsyncSession | Session
    ):
        """
        Delete shipping address for an order (e.g., when order is cancelled).

        Args:
            order_id: Order ID
            session: Database session
        """
        stmt = select(ShippingAddress).where(ShippingAddress.order_id == order_id)
        result = await session_execute(stmt, session)
        shipping_address = result.scalar_one_or_none()

        if shipping_address:
            await session.delete(shipping_address)
            await session_commit(session)

    @staticmethod
    async def check_cart_has_physical_items(cart_items, session: AsyncSession | Session) -> bool:
        """
        Check if cart contains any physical items requiring shipping.

        Args:
            cart_items: List of CartItemDTO objects
            session: Database session

        Returns:
            True if cart has physical items, False otherwise
        """
        from repositories.item import ItemRepository
        from models.item import ItemDTO

        for cart_item in cart_items:
            item = await ItemRepository.get_single(
                cart_item.category_id,
                cart_item.subcategory_id,
                session
            )
            if item and item.is_physical:
                return True

        return False
