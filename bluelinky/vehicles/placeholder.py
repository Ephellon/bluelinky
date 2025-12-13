"""Placeholder vehicle for regions without a full Python port yet."""
from __future__ import annotations

from ..interfaces import (
    FullVehicleStatus,
    RawVehicleStatus,
    VehicleLocation,
    VehicleOdometer,
    VehicleRegisterOptions,
    VehicleStartOptions,
    VehicleStatus,
    VehicleStatusOptions,
)
from .base import Vehicle


class PlaceholderVehicle(Vehicle):
    """Vehicle that mirrors the public API but raises informative errors."""

    def _not_ported(self) -> None:
        raise NotImplementedError(
            "This regional vehicle implementation has not been fully ported to Python yet."
        )

    def status(self, input: VehicleStatusOptions) -> VehicleStatus | RawVehicleStatus | None:
        self._not_ported()

    def full_status(self, input: VehicleStatusOptions) -> FullVehicleStatus | None:
        self._not_ported()

    def unlock(self) -> str:
        self._not_ported()

    def lock(self) -> str:
        self._not_ported()

    def start(self, config: VehicleStartOptions) -> str:
        self._not_ported()

    def stop(self) -> str:
        self._not_ported()

    def location(self) -> VehicleLocation | None:
        self._not_ported()

    def odometer(self) -> VehicleOdometer | None:
        self._not_ported()
