"""Python port entrypoint."""
from __future__ import annotations

from typing import List, Optional

from .constants import DEFAULT_CONFIG, Region
from .controllers.american import AmericanController
from .controllers.australia import AustraliaController
from .controllers.canadian import CanadianController
from .controllers.chinese import ChineseController
from .controllers.european import EuropeanController
from .controllers.base import SessionController
from .interfaces import BlueLinkyConfig, Session
from .logger import logger
from .vehicles.american import AmericanVehicle
from .vehicles.base import Vehicle
from .vehicles.placeholder import PlaceholderVehicle


class BlueLinky:
    def __init__(self, config: BlueLinkyConfig) -> None:
        self.config = self._merge_config(config)
        self.controller: SessionController = self._build_controller()
        self.vehicles: List[Vehicle] = []
        if self.config.auto_login:
            logger.debug("Bluelinky is logging in automatically, to disable use auto_login=False")
            self.login()

    def _merge_config(self, config: BlueLinkyConfig) -> BlueLinkyConfig:
        merged = {**DEFAULT_CONFIG, **config.__dict__}
        return BlueLinkyConfig(**merged)

    def _build_controller(self) -> SessionController:
        region = self.config.region
        if region == Region.EU:
            return EuropeanController(self.config)
        if region == Region.US:
            return AmericanController(self.config)
        if region == Region.CA:
            return CanadianController(self.config)
        if region == Region.CN:
            return ChineseController(self.config)
        if region == Region.AU:
            return AustraliaController(self.config)
        raise ValueError("Unsupported region")

    def on_ready(self) -> List[Vehicle]:
        return self.vehicles

    def login(self) -> str:
        response = self.controller.login()
        self.vehicles = self.get_vehicles()
        logger.debug("Found %s vehicles on the account", len(self.vehicles))
        return response

    def refresh_access_token(self) -> str:
        return self.controller.refresh_access_token()

    def logout(self) -> str:
        return self.controller.logout()

    def get_vehicles(self) -> List[Vehicle]:
        vehicles = self.controller.get_vehicles()
        return vehicles or []

    def get_vehicle(self, vin: str) -> Optional[Vehicle]:
        for vehicle in self.vehicles:
            if vehicle.vin().lower() == vin.lower():
                return vehicle
        if self.vehicles:
            raise ValueError(f"Could not find vehicle with id: {vin}")
        return None

    def get_session(self) -> Session:
        return self.controller.session

    @property
    def cached_vehicles(self) -> List[Vehicle]:
        return self.vehicles


__all__ = [
    "BlueLinky",
    "Region",
    "Vehicle",
    "AmericanVehicle",
    "PlaceholderVehicle",
]
