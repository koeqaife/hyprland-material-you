import re
import datetime

__all__ = [
    "get_formatted_date", "get_formatted_time",
    "get_layout_tag"
]


def get_layout_tag(layout: str) -> str:
    match = re.search(r'\(([^)]+)\)', layout)
    if match:
        region = match.group(1).strip()
        return region[:2].lower()
    else:
        lang = layout.strip().split()[0]
        return lang[:2].lower()


def get_formatted_date(date: datetime.datetime) -> str:
    year = date.year
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"
    return f"{year}-{month}-{day}"


def get_formatted_time(
    date: datetime.datetime,
    is_12_hour: bool = False
) -> str:
    hours = date.hour
    minutes = f"{date.minute:02d}"

    if is_12_hour:
        period = "AM" if hours < 12 else "PM"
        hours = hours % 12
        hours = 12 if hours == 0 else hours
        return f"{hours}:{minutes} {period}"
    else:
        return f"{hours:02d}:{minutes}"


def get_full_date(
    date: datetime.datetime
) -> str:
    return date.strftime('%A, %d %b %Y')


def escape_markup(text: str) -> str:
    escape_dict = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }

    return ''.join(escape_dict.get(c, c) for c in text)
