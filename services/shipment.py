from sqlalchemy import select

from db import async_session_maker
from models.shipment import Shipment


class ShipmentService:

    @staticmethod
    async def get_or_create_one(shipment_name: str) -> Shipment:
        async with async_session_maker() as session:
            stmt = select(Shipment).where(Shipment.name == shipment_name)
            shipment = await session.execute(stmt)
            shipment = shipment.scalar()
            if shipment is None:
                new_shipment_obj = Shipment(name=shipment_name)
                session.add(new_shipment_obj)
                await session.commit()
                await session.refresh(new_shipment_obj)
                return new_shipment_obj
            else:
                return shipment

    @staticmethod
    async def get_by_primary_key(primary_key: int) -> Shipment:
        async with async_session_maker() as session:
            stmt = select(Shipment).where(Shipment.id == primary_key)
            shipment = await session.execute(stmt)
            return shipment.scalar()

    @staticmethod
    async def get_all_shipment_options():
        async with async_session_maker() as session:
            stmt = select(Shipment).distinct()
            shipment = await session.execute(stmt)
            return shipment.scalars().all()
