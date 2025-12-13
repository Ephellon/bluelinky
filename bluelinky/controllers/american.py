"""American region controller."""
from __future__ import annotations

import time
from typing import List

from ..constants import Region
from ..interfaces import BlueLinkyConfig, VehicleRegisterOptions
from ..logger import logger
from ..vehicles.american import AmericanVehicle
from .base import SessionController


class AmericanController(SessionController):
    region = Region.US

    def __init__(self, user_config: BlueLinkyConfig) -> None:
        super().__init__(user_config)
        self._environment = _get_brand_environment(user_config.brand)
        self.vehicles: List[AmericanVehicle] = []
        logger.debug("US Controller created")

    @property
    def environment(self):
        return self._environment

    def refresh_access_token(self) -> str:
        if not self.session.refresh_token:
            return "No refresh token available"
        if not self.token_expired():
            return "Token not expired, no need to refresh"

        response = self.http.post(
            f"{self.environment['base_url']}/v2/ac/oauth/token/refresh",
            json={"refresh_token": self.session.refresh_token},
            headers={
                "User-Agent": "python-bluelinky",
                "client_secret": self.environment["client_secret"],
                "client_id": self.environment["client_id"],
            },
        )
        response.raise_for_status()
        body = response.json()
        self.session.access_token = body["access_token"]
        self.session.refresh_token = body.get("refresh_token", self.session.refresh_token)
        self.session.token_expires_at = int(time.time()) + int(body.get("expires_in", 0))
        logger.debug("Token refreshed")
        return "Token refreshed"

    def login(self) -> str:
        response = self.http.post(
            f"{self.environment['base_url']}/v2/ac/oauth/token",
            json={"username": self.user_config.username, "password": self.user_config.password},
            headers={
                "User-Agent": "python-bluelinky",
                "client_id": self.environment["client_id"],
                "client_secret": self.environment["client_secret"],
            },
        )
        response.raise_for_status()
        body = response.json()
        self.session.access_token = body["access_token"]
        self.session.refresh_token = body.get("refresh_token", "")
        self.session.token_expires_at = int(time.time()) + int(body.get("expires_in", 0))
        return "login good"

    def logout(self) -> str:
        return "OK"

    def get_vehicles(self) -> List[AmericanVehicle]:
        response = self.http.get(
            f"{self.environment['base_url']}/ac/v2/enrollment/details/{self.user_config.username}",
            headers={
                "access_token": self.session.access_token,
                "client_id": self.environment["client_id"],
                "Host": self.environment["host"],
                "User-Agent": "python-bluelinky",
                "includeNonConnectedVehicles": "Y",
            },
        )
        response.raise_for_status()
        data = response.json()
        vehicles = []
        for entry in data.get("enrolledVehicleDetails", []):
            info = entry.get("vehicleDetails", {})
            vehicle_config = VehicleRegisterOptions(
                nickname=info.get("nickName", ""),
                name=info.get("nickName", ""),
                vin=info.get("vin", ""),
                reg_date=info.get("enrollmentDate", ""),
                brand_indicator=info.get("brandIndicator"),
                reg_id=info.get("regid"),
                generation=str(info.get("vehicleGeneration")),
            )
            ev_status = info.get("evStatus")
            if ev_status == "N":
                vehicle_config.engine_type = "ICE"
            elif ev_status == "E":
                vehicle_config.engine_type = "EV"
            vehicles.append(AmericanVehicle(vehicle_config, self))
        self.vehicles = vehicles
        return self.vehicles


def _get_brand_environment(brand: str) -> dict:
    brand = brand.lower()
    if brand == "kia":
        client_id = "14a22b0a-91d3-4e45-ab92-fc42f3c9d750"
        client_secret = "c3dcbf6f-1c36-4b0d-82f0-71652d7a2606"
    else:
        client_id = "101e9585-302d-4c14-8c25-9ec6e6b57e43"
        client_secret = "8f43e78e-6f59-4a43-b2d2-1639f56edb83"
    return {
        "base_url": "https://api.telematics.hyundaiusa.com",
        "client_id": client_id,
        "client_secret": client_secret,
        "host": "api.telematics.hyundaiusa.com",
    }
