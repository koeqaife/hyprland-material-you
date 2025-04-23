from utils import Ref, get_formatted_date, get_formatted_time
from config import Settings
import datetime
import asyncio

time = Ref("00:00", name="time")
date = Ref("1997-01-01", name="date")


async def clock_task() -> None:
    settings = Settings()

    is_12_hour = False

    def settings_update(format: str) -> None:
        nonlocal is_12_hour

        is_12_hour = format != "24"
        now = datetime.datetime.now()
        update_time_date(now)

    def update_time_date(_date: datetime.datetime) -> None:
        nonlocal is_12_hour

        time.value = get_formatted_time(_date, is_12_hour)
        date.value = get_formatted_date(_date)

    settings.subscribe("time_format", settings_update)

    while True:
        now = datetime.datetime.now()
        update_time_date(now)

        next_minute = (
            (now + datetime.timedelta(minutes=1))
            .replace(second=0, microsecond=0)
        )
        sleep_duration = (next_minute - now).total_seconds()
        await asyncio.sleep(sleep_duration)
