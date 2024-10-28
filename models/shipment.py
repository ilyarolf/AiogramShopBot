from sqlalchemy import Column, Integer, String, Float, Boolean

from models.base import Base


class Shipment(Base):
    __tablename__ = 'shipment'

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False, unique=False)
    is_default = Column(Boolean, nullable=False, default=False)
    price = Column(Float, nullable=False)
    is_insured = Column(Boolean, nullable=False, default=False)
    description = Column(String, nullable=False)
