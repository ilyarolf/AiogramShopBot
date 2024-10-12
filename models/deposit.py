from sqlalchemy import Integer, Column, String, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship, backref

from models.base import Base


class Deposit(Base):
    __tablename__ = 'deposits'
    id = Column(Integer, primary_key=True)
    tx_id = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", backref=backref("users",lazy="joined"))
    network = Column(String, nullable=False)
    token_name = Column(String, nullable=True)
    amount = Column(BigInteger, nullable=False)
    is_withdrawn = Column(Boolean, default=False)
    vout = Column(Integer, nullable=False)
