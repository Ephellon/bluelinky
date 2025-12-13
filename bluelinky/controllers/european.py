"""European controller placeholder."""
from __future__ import annotations

from ..constants import Region
from ..interfaces import BlueLinkyConfig
from .placeholder import PlaceholderController


class EuropeanController(PlaceholderController):
    region = Region.EU

    def __init__(self, user_config: BlueLinkyConfig) -> None:
        super().__init__(user_config, "European")
