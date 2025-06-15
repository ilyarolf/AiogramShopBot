from pydantic import BaseModel

from enums.cryptocurrency import Cryptocurrency
from enums.withdraw_type import WithdrawType


class WithdrawalDTO(BaseModel):
    withdrawType: WithdrawType
    cryptoCurrency: Cryptocurrency
    toAddress: str
    txIdList: list = []
    receivingAmount: float | None = None
    blockchainFeeAmount: float | None = None
    serviceFeeAmount: float | None = None
    onlyCalculate: bool
    totalWithdrawalAmount: float | None = None
