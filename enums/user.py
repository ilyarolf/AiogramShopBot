from enum import Enum


class UserResponse(Enum):
    BALANCE_REFRESHED = 1
    BALANCE_NOT_REFRESHED = 2
    BALANCE_REFRESH_COOLDOWN = 3
