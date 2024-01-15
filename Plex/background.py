from datetime import date, datetime, timedelta, timezone
import aiohttp
import discord
from tunables import *

def this_week() -> str:

    day = f"{date.today()}"
    # print(f"day == {day}")
    dt = datetime.strptime(day, '%Y-%m-%d')
    dt = dt + timedelta(days=1)
    dt = dt.replace(tzinfo=timezone.utc)
    # print(f"dt == {dt}")
    # print(f"dt.weekday() == {dt.weekday()}")
    start = dt - timedelta(days=dt.weekday() + 1)
    # print(f"start == {start}")
    end = start + timedelta(days=7)
    # print(f"end == {end}")
    
    start = str(start).split()
    end = str(end).split()
    
    return start[0], end[0]

def end_of_week_int() -> int:
    start, end = this_week()
    val = datetime.strptime(end, "%Y-%m-%d")
    return int(val.timestamp())

def end_of_day_int() -> int:
    now = datetime.now()
    next_day = now + timedelta(days=1)
    # next_day = next_day.replace(tzinfo=timezone.utc)
    next_day_midnight = next_day.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(next_day_midnight.timestamp())

def utc_to_central(t) -> datetime:

    val = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
    val = val - timedelta(hours=6)

    return val

def day_to_int(t) -> int:
    val = datetime.strptime(str(t).split()[0], "%Y-%m-%d")
    return int(val.timestamp())

def int_to_weekday(d) -> str:

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    return days[d]