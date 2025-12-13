"""Utility helpers ported from the TypeScript implementation."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List

from .constants import Region


def celsius_to_temp_code(region: Region, temperature: float) -> str:
    ranges = _temperature_range(region)
    try:
        index = ranges.index(temperature)
    except ValueError as exc:  # pragma: no cover - caller should validate
        raise ValueError(f"Unsupported temperature {temperature} for region {region}") from exc
    return f"{index:02X}H".rjust(3, "0")


def temp_code_to_celsius(region: Region, code: str) -> float:
    ranges = _temperature_range(region)
    index = int(code.rstrip("H"), 16)
    return ranges[index]


def parse_date(value: str) -> datetime:
    year = int(value[0:4])
    month = int(value[4:6])
    if len(value) <= 6:
        return datetime(year, month, 1)
    day = int(value[6:8])
    if len(value) <= 8:
        return datetime(year, month, day)
    hour = int(value[8:10])
    minute = int(value[10:12])
    second = int(value[12:14])
    return datetime(year, month, day, hour, minute, second)


def add_minutes(date: datetime, minutes: int) -> datetime:
    return date + timedelta(minutes=minutes)


def _temperature_range(region: Region) -> List[float]:
    if region == Region.US:
        start, end = 14, 30
    elif region == Region.CA:
        start, end = 16, 32
    elif region == Region.AU:
        start, end = 17, 27
    else:
        start, end = 14, 30
    step = 0.5
    return [round(start + i * step, 2) for i in range(int((end - start) / step) + 1)]


def async_map(iterable: Iterable, func):  # pragma: no cover - parity helper
    return [func(item) for item in iterable]
