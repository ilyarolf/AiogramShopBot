from enum import Enum


class RuntimeEnvironment(str, Enum):
    DEV = "DEV"
    PROD = "PROD"
    TEST = "TEST"  # For test scripts - no webhook/ngrok setup
