from enum import Enum


class RuntimeEnvironment(str, Enum):
    DEV = 1
    PROD = 2
