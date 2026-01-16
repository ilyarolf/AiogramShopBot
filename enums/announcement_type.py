from enum import IntEnum


class AnnouncementType(IntEnum):
    RESTOCKING = 1
    CURRENT_STOCK = 2
    FROM_RECEIVING_MESSAGE = 3
