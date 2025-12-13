from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

from .client import BlueLinky
from .constants import Region
from .interfaces import BlueLinkyConfig, Brand
from .logger import logger


ENV_VARS = {
   "username": "BLUELINKY_USERNAME",
   "password": "BLUELINKY_PASSWORD",
   "region": "BLUELINKY_REGION",
   "brand": "BLUELINKY_BRAND",
   "pin": "BLUELINKY_PIN",
   "vin": "BLUELINKY_VIN",
   "vehicle_id": "BLUELINKY_VEHICLE_ID",
}


def _parse_region(value: str) -> Region:
   return Region[value.strip().upper()]


def _parse_brand(value: str) -> Brand:
   return Brand(value.strip().lower())


def load_config_from_file(path: Path) -> Optional[BlueLinkyConfig]:
   if not path.exists():
      return None
   try:
      raw = json.loads(path.read_text())
   except json.JSONDecodeError as exc:  # pragma: no cover - defensive
      logger.error("Failed to parse config file %s: %s", path, exc)
      return None
   try:
      region_value = raw.get("region")
      brand_value = raw.get("brand", Brand.HYUNDAI.value)
      return BlueLinkyConfig(
         username=raw.get("username"),
         password=raw.get("password"),
         region=_parse_region(region_value),
         brand=_parse_brand(brand_value),
         auto_login=bool(raw.get("auto_login", True)),
         pin=raw.get("pin"),
         vin=raw.get("vin"),
         vehicle_id=raw.get("vehicle_id"),
      )
   except Exception as exc:  # pragma: no cover - defensive
      logger.error("Invalid configuration in %s: %s", path, exc)
      return None


def load_config_from_env() -> Optional[BlueLinkyConfig]:
   username = os.environ.get(ENV_VARS["username"])
   password = os.environ.get(ENV_VARS["password"])
   region_raw = os.environ.get(ENV_VARS["region"])
   brand_raw = os.environ.get(ENV_VARS["brand"], Brand.HYUNDAI.value)
   pin = os.environ.get(ENV_VARS["pin"])
   vin = os.environ.get(ENV_VARS["vin"])
   vehicle_id = os.environ.get(ENV_VARS["vehicle_id"])
   if not region_raw:
      return None
   return BlueLinkyConfig(
      username=username,
      password=password,
      region=_parse_region(region_raw),
      brand=_parse_brand(brand_raw),
      pin=pin,
      vin=vin,
      vehicle_id=vehicle_id,
   )


def resolve_config() -> Optional[BlueLinkyConfig]:
   env_config = load_config_from_env()
   if env_config:
      return env_config
   config_path = os.environ.get("BLUELINKY_CONFIG", "~/.bluelinky.json")
   return load_config_from_file(Path(config_path).expanduser())


def main() -> None:
   logger.setLevel(os.environ.get("BLUELINKY_LOG_LEVEL", "INFO"))
   config = resolve_config()
   if not config or not config.username or not config.password or not config.pin:
      message = (
         "Missing configuration. Set environment variables"
         f" {', '.join(ENV_VARS.values())} or provide a JSON file via BLUELINKY_CONFIG."
      )
      print(message)
      return
   try:
      client = BlueLinky(config)
      print(
         f"Initialized BlueLinky for {config.username} in region {config.region.value}. "
         f"Vehicles: {len(client.cached_vehicles)}"
      )
   except Exception as exc:  # pragma: no cover - runtime guard
      print(f"Failed to initialize BlueLinky: {exc}", file=sys.stderr)
      sys.exit(1)


if __name__ == "__main__":
   main()
