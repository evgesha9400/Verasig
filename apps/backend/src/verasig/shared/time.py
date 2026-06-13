from datetime import datetime

_MONTHS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def format_long(value: datetime) -> str:
    return f"{_MONTHS[value.month]} {value.day}, {value.year}"


def format_short(value: datetime) -> str:
    return f"{_MONTHS[value.month]} {value.day}"


def format_time(value: datetime) -> str:
    return value.strftime("%H:%M")
