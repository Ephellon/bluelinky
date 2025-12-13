"""Placeholder controller for regions not yet ported."""
from __future__ import annotations

from typing import List

from ..interfaces import BlueLinkyConfig
from ..vehicles.placeholder import PlaceholderVehicle
from .base import SessionController


class PlaceholderController(SessionController):
    def __init__(self, user_config: BlueLinkyConfig, region_label: str) -> None:
        super().__init__(user_config)
        self.region_label = region_label

    def login(self) -> str:
        raise NotImplementedError(f"{self.region_label} region is not yet ported to Python")

    def get_vehicles(self) -> List[PlaceholderVehicle]:
        return []

    def refresh_access_token(self) -> str:
        raise NotImplementedError(f"{self.region_label} region is not yet ported to Python")
