"""Vehicle base implementation."""
from __future__ import annotations

from typing import Optional

from ..constants import Region
from ..interfaces import (
    BlueLinkyConfig,
    FullVehicleStatus,
    RawVehicleStatus,
    VehicleLocation,
    VehicleOdometer,
    VehicleRegisterOptions,
    VehicleStartOptions,
    VehicleStatus,
    VehicleStatusOptions,
)


class Vehicle:
    region: Region

    def __init__(self, vehicle_config: VehicleRegisterOptions, controller) -> None:
        self.vehicle_config = vehicle_config
        self.controller = controller
        self.user_config: BlueLinkyConfig = controller.user_config
        self._full_status: Optional[FullVehicleStatus] = None
        self._status: Optional[VehicleStatus | RawVehicleStatus] = None
        self._location: Optional[VehicleLocation] = None
        self._odometer: Optional[VehicleOdometer] = None

    # region helper methods
    def vin(self) -> str:
        return self.vehicle_config.vin

    def name(self) -> str:
        return self.vehicle_config.name

    def nickname(self) -> str:
        return self.vehicle_config.nickname

    def id(self) -> Optional[str]:
        return self.vehicle_config.id

    def brand_indicator(self) -> Optional[str]:
        return self.vehicle_config.brand_indicator

    # region required overrides
    def status(self, input: VehicleStatusOptions) -> VehicleStatus | RawVehicleStatus | None:
        raise NotImplementedError

    def full_status(self, input: VehicleStatusOptions) -> FullVehicleStatus | None:
        raise NotImplementedError

    def unlock(self) -> str:
        raise NotImplementedError

    def lock(self) -> str:
        raise NotImplementedError

    def start(self, config: VehicleStartOptions) -> str:
        raise NotImplementedError

    def stop(self) -> str:
        raise NotImplementedError

    def location(self) -> VehicleLocation | None:
        raise NotImplementedError

    def odometer(self) -> VehicleOdometer | None:
        raise NotImplementedError
