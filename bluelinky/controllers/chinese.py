"""Chinese controller placeholder."""
from __future__ import annotations

from ..constants import Region
from ..interfaces import BlueLinkyConfig
from .placeholder import PlaceholderController


class ChineseController(PlaceholderController):
    region = Region.CN

    def __init__(self, user_config: BlueLinkyConfig) -> None:
        super().__init__(user_config, "Chinese")
