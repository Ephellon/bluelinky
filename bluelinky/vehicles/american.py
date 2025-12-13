"""US vehicle implementation."""
from __future__ import annotations

from typing import Optional

from ..constants import DEFAULT_VEHICLE_STATUS_OPTIONS, Region
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
from ..logger import logger
from .base import Vehicle


class AmericanVehicle(Vehicle):
    region = Region.US

    def __init__(self, vehicle_config: VehicleRegisterOptions, controller) -> None:
        super().__init__(vehicle_config, controller)
        logger.debug("US Vehicle %s created", self.vehicle_config.vin)

    def _headers(self) -> dict:
        return {
            "access_token": self.controller.session.access_token,
            "client_id": self.controller.environment["client_id"],
            "Host": self.controller.environment["host"],
            "User-Agent": "python-bluelinky",
            "registrationId": self.vehicle_config.reg_id or "",
            "gen": self.vehicle_config.generation or "",
            "username": self.user_config.username,
            "vin": self.vehicle_config.vin,
            "APPCLOUD-VIN": self.vehicle_config.vin,
            "Language": "0",
            "to": "ISS",
            "encryptFlag": "false",
            "from": "SPA",
            "brandIndicator": self.vehicle_config.brand_indicator or "",
            "bluelinkservicepin": self.user_config.pin,
            "offset": "-5",
        }

    def _request(self, path: str, method: str = "GET", json_body: Optional[dict] = None):
        url = f"{self.controller.environment['base_url']}{path if path.startswith('/') else '/' + path}"
        response = self.controller.http.request(method, url, headers=self._headers(), json=json_body)
        response.raise_for_status()
        return response

    def status(self, input: VehicleStatusOptions = DEFAULT_VEHICLE_STATUS_OPTIONS) -> VehicleStatus | RawVehicleStatus | None:
        response = self._request(
            "/ac/v2/rcs/rsc/status",
            method="GET",
        )
        body = response.json()
        self._status = VehicleStatus(state=body)
        return self._status

    def full_status(self, input: VehicleStatusOptions = DEFAULT_VEHICLE_STATUS_OPTIONS) -> FullVehicleStatus | None:
        response = self._request(
            "/ac/v2/rcs/rsc/advanced",
            method="GET",
        )
        self._full_status = FullVehicleStatus(raw=response.json())
        return self._full_status

    def unlock(self) -> str:
        self._request("/ac/v2/rcs/rsc/door/unlock", method="POST")
        return "unlock started"

    def lock(self) -> str:
        self._request("/ac/v2/rcs/rsc/door/lock", method="POST")
        return "lock started"

    def start(self, config: VehicleStartOptions) -> str:
        payload = {
            "Ims": 0,
            "airCtrl": int(bool(config.get("hvac", False))),
            "airTemp": {"unit": 1, "value": f"{config.get('temperature', 70)}"},
            "defrost": config.get("defrost", False),
            "heating1": config.get("heated_features", 0),
            "igniOnDuration": config.get("duration", 10),
            "seatHeaterVentInfo": config.get("seat_climate_settings"),
            "username": self.user_config.username,
            "vin": self.vehicle_config.vin,
        }
        self._request("/ac/v2/rcs/rsc/start", method="POST", json_body=payload)
        return "start command issued"

    def stop(self) -> str:
        self._request("/ac/v2/rcs/rsc/stop", method="POST")
        return "stop command issued"

    def location(self) -> VehicleLocation | None:
        response = self._request("/ac/v2/rcs/rfc/findMyCar", method="GET")
        data = response.json()
        location = VehicleLocation(
            latitude=data.get("coord", {}).get("lat", 0),
            longitude=data.get("coord", {}).get("lon", 0),
            altitude=data.get("coord", {}).get("alt"),
            heading=data.get("head"),
            speed=data.get("speed", {}),
        )
        self._location = location
        return location

    def odometer(self) -> VehicleOdometer | None:
        response = self._request(
            f"/ac/v2/enrollment/details/{self.user_config.username}",
            method="GET",
        )
        data = response.json()
        for item in data.get("enrolledVehicleDetails", []):
            if item.get("vehicleDetails", {}).get("vin") == self.vin():
                info = item["vehicleDetails"]
                self._odometer = VehicleOdometer(value=info.get("odometer", 0), unit=0)
                return self._odometer
        return None
