from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Integer, Column, ForeignKey, BigInteger, DateTime, func, CheckConstraint, Enum, Float

import config
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from models.base import Base
from utils.utils import get_text


class Deposit(Base):
    __tablename__ = 'deposits'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    network = Column(Enum(Cryptocurrency), nullable=False)
    amount = Column(BigInteger, nullable=False)
    deposit_datetime = Column(DateTime, default=func.now())
    fiat_amount = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint('amount > 0', name='check_amount_positive'),
        CheckConstraint('fiat_amount >= 0', name='check_fiat_amount'),
    )


class DepositDTO(BaseModel):
    id: int | None = None
    user_id: int | None = None
    network: Cryptocurrency | None = None
    amount: int | None = None
    deposit_datetime: datetime | None = None
    fiat_amount: float | None = None

    @staticmethod
    def get_chart_text(language: Language) -> tuple[str, str]:
        return (get_text(language, BotEntity.ADMIN, "deposit_ylabel")
                .format(currency_sym=config.CURRENCY.get_localized_symbol()),
                get_text(language, BotEntity.ADMIN, "deposit_chart_title"))
