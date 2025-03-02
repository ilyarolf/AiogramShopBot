from enum import Enum


class RuntimeEnvironment(str, Enum):
    DEV = "DEV"
    PROD = "PROD"
