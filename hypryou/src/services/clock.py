from utils import Ref, get_formatted_date, get_formatted_time
from utils import get_full_date
from config import Settings
import datetime
import asyncio
from utils.service import AsyncService

time = Ref("00:00", name="time")
date = Ref("1997-01-01", name="date")
full_date = Ref("...", name="full_date")


class ClockService(AsyncService):
    async def start(self) -> None:
        settings = Settings()

        is_24hr_clock = True

        def settings_update(_is_24hr_clock: bool) -> None:
            nonlocal is_24hr_clock
            is_24hr_clock = _is_24hr_clock
            update_time_date(datetime.datetime.now())

        def update_time_date(_date: datetime.datetime) -> None:
            time.value = get_formatted_time(_date, not is_24hr_clock)
            date.value = get_formatted_date(_date)
            full_date.value = get_full_date(_date)

        settings.watch("is_24hr_clock", settings_update)

        while True:
            now = datetime.datetime.now()
            update_time_date(now)

            next_minute = (
                (now + datetime.timedelta(minutes=1))
                .replace(second=0, microsecond=0)
            )
            sleep_duration = (next_minute - now).total_seconds()
            await asyncio.sleep(sleep_duration)
