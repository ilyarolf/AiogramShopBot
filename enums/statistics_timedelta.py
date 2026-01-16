import calendar
from datetime import datetime, timedelta
from enum import IntEnum


class StatisticsTimeDelta(IntEnum):
    DAY = 1
    WEEK = 7
    MONTH = 30

    def get_time_range(self) -> tuple[datetime, datetime]:
        now = datetime.now()

        match self:
            case StatisticsTimeDelta.DAY:
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            case StatisticsTimeDelta.WEEK:
                start = now - timedelta(days=now.weekday())
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=6)
                end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

            case _:
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                _, last_day = calendar.monthrange(now.year, now.month)
                end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

        return start, end
