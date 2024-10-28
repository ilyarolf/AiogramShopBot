from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref

from models.base import Base


class Shipment(Base):
    __tablename__ = 'shipment'

    id = Column(Integer, primary_key=True, unique=True)

    name = Column(String, nullable=False, unique=False)
    price = Column(Float, nullable=False)
    is_insured = Column(Boolean, nullable=False, default=False)
    description = Column(String, nullable=False)
