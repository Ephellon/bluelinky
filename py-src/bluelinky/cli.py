# This is an updated version of the BlueLinky CLI that includes a
# `list` command to enumerate all vehicles.  This allows you to verify
# that your credentials are working and to see the vehicles on your
# account without selecting a specific one.  The rest of the CLI
# commands (status, lock, unlock, horn, flash, locate) remain unchanged.

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from . import BlueLinky, Region
from .interfaces import BlueLinkyConfig
from .interfaces.common_interfaces import VehicleStartOptions, VehicleStatusOptions
from .tools.common_tools import haversine_km


DEFAULT_CONFIG_PATHS = [
   Path(os.getenv("BLUELINKY_CONFIG", "")),
   Path.home() / ".bluelinky" / "config.json",
   Path("config.json"),
]


log = logging.getLogger("bluelinky.cli")


def resolve_config_path(path: Optional[str] = None) -> Path:
   """
   Resolve the actual config file path that will be used.
   Resolution order:
   1. --config argument (if given)
   2. BLUELINKY_CONFIG environment variable
   3. ~/.bluelinky/config.json
   4. ./config.json
   """
   candidates: list[Path] = []

   if path:
      candidates.append(Path(path))

   env_path = os.getenv("BLUELINKY_CONFIG")
   if env_path:
      candidates.append(Path(env_path))

   candidates.extend(DEFAULT_CONFIG_PATHS[1:])

   for p in candidates:
      if p and p.is_file():
         return p

   raise FileNotFoundError(
      "No config file found. "
      "Tried: --config, BLUELINKY_CONFIG, ~/.bluelinky/config.json, ./config.json"
   )


def save_config(path: Path, data: dict) -> None:
   path.parent.mkdir(parents=True, exist_ok=True)
   with path.open("w", encoding="utf-8") as f:
      json.dump(data, f, indent=4)
      f.write("\n")


def load_config(path: Optional[str] = None) -> dict:
   p = resolve_config_path(path)
   with p.open("r", encoding="utf-8") as f:
      return json.load(f)


def _convert_temperature(value: int, from_unit: str, to_unit: str) -> int:
   if from_unit == to_unit:
      return value

   if from_unit == "C" and to_unit == "F":
      return int(round((value * 9 / 5) + 32))

   if from_unit == "F" and to_unit == "C":
      return int(round((value - 32) * 5 / 9))

   return value


def _clamp_temperature(value: int, unit: str) -> int:
   if unit == "F":
      return max(61, min(83, value))
   return max(16, min(28, value))


def _parse_temperature_arg(value: str) -> tuple[int, str]:
   raw = str(value).strip()
   if not raw:
      raise argparse.ArgumentTypeError("temperature value cannot be empty")

   unit = None
   if raw[-1].upper() in ("C", "F") and len(raw) > 1:
      unit = raw[-1].upper()
      raw = raw[:-1]

   try:
      temp = float(raw)
   except ValueError as exc:
      raise argparse.ArgumentTypeError(f"invalid temperature: {value!r}") from exc

   if unit is None:
      unit = "C" if temp <= 45 else "F"

   clamped = int(round(temp))
   if unit == "F":
      clamped = max(61, min(83, clamped))
   else:
      clamped = max(16, min(28, clamped))

   return clamped, unit


def _parse_time_arg(value: str) -> int:
   try:
      minutes = int(value)
   except ValueError as exc:
      raise argparse.ArgumentTypeError(f"invalid time value: {value!r}") from exc

   return max(1, min(30, minutes))


def _parse_heat_arg(value: str) -> str:
   normalized = str(value).strip().lower()
   if normalized in ("yes", "on", "true", "1"):
      return "on"
   if normalized == "all":
      return "all"
   if normalized == "defrost":
      return "defrost"

   raise argparse.ArgumentTypeError("--heat must be one of: yes, on, true, 1, all, defrost")


def make_client(cfg_data: dict) -> BlueLinky:
   unknown = set(cfg_data.keys()) - set(BlueLinkyConfig.__annotations__.keys())
   if unknown:
      print(f"Ignoring unknown config keys: {sorted(unknown)}")

   region_value = cfg_data.get("region", "US")
   try:
      region = Region[region_value.upper()]
   except KeyError:
      raise ValueError(f"Unknown region: {region_value!r}")

   home = cfg_data.get("home")
   home_tuple = None
   if isinstance(home, (list, tuple)) and len(home) >= 2:
      lat = float(home[0])
      lon = float(home[1])
      alt = float(home[2]) if len(home) > 2 and home[2] is not None else 0.0
      home_tuple = (lat, lon, alt)

   cfg = BlueLinkyConfig(
      username=cfg_data["username"],
      password=cfg_data["password"],
      pin=str(cfg_data["pin"]),
      brand=cfg_data.get("brand", "hyundai"),
      region=region,
      vin=cfg_data.get("vin"),
      home=home_tuple,
   )

   return BlueLinky(cfg)


def pick_vehicle(client: BlueLinky, cfg_data: dict):
   vin = cfg_data.get("vin")
   if vin:
      vehicle = client.getVehicle(vin)
      if vehicle is None:
         raise RuntimeError(f"Vehicle with VIN {vin!r} not found.")
      return vehicle

   vehicles = client.getVehicles()
   if not vehicles:
      raise RuntimeError("No vehicles found on this account.")
   if len(vehicles) > 1:
      log.warning("Multiple vehicles found; using the first one.")
   return vehicles[0]


def cmd_status(client, vehicle, args):
   status = vehicle.status()
   if status is None:
      print("No status returned.")
      return 1

   try:
      data = asdict(status)
   except TypeError:
      data = status

   print(json.dumps(data, indent=2, default=str))
   return 0


def cmd_lock(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   res = vehicle.lock()
   print("Lock command sent:", res)
   return 0


def cmd_unlock(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   res = vehicle.unlock()
   print("Unlock command sent:", res)
   return 0


def cmd_horn(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   res = vehicle.horn()
   print("Horn command sent:", res)
   return 0


def cmd_flash(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   # adjust name if your API uses `lights()` / `light()` / `flash()`
   res = vehicle.light()
   print("Lights command sent:", res)
   return 0


def _heat_mode_from_arg(value: Optional[str]) -> tuple[bool, bool, str]:
   if value is None:
      return False, False, "off"

   if value == "on":
      return True, False, "on"
   if value == "all":
      return True, True, "all"
   if value == "defrost":
      return False, True, "defrost"

   return False, False, "off"


def _target_unit_for_vehicle(vehicle) -> str:
   vehicle_region = getattr(vehicle, "region", None)
   return "F" if vehicle_region == Region.US else "C"


def cmd_start(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   try:
      heat_on, defrost_on, heat_mode = _heat_mode_from_arg(getattr(args, "heat", None))

      target_unit = _target_unit_for_vehicle(client)
      default_temp = 72 if target_unit == "F" else 22

      temp_value: Optional[int] = None
      temp_unit: str = target_unit
      if getattr(args, "temp", None) is not None:
         parsed_temp, parsed_unit = args.temp
         temp_value = _clamp_temperature(
            _convert_temperature(parsed_temp, parsed_unit, target_unit),
            target_unit,
         )
         temp_unit = target_unit
      else:
         if heat_on or defrost_on:
            temp_value = default_temp
            temp_unit = target_unit

      hvac_on = bool((getattr(args, "temp", None) is not None) or heat_on or defrost_on)
      duration = getattr(args, "time", None)
      if duration is None:
         duration = 10

      start_options = VehicleStartOptions(
         hvac=hvac_on,
         duration=duration,
         temperature=temp_value if temp_value is not None else default_temp,
         defrost=defrost_on,
         heatedFeatures=1 if heat_on else 0,
         unit=temp_unit,
         seatClimateSettings={},
      )

      log.info(
         "Starting vehicle for %s minutes at %s%s (heat=%s)",
         duration,
         start_options.temperature,
         temp_unit,
         heat_mode,
      )

      res = vehicle.start(start_options)
      print(res)
      return 0
   except argparse.ArgumentTypeError as exc:
      parser = build_parser()
      parser.error(str(exc))
   except Exception as exc:
      print(str(exc))
      return 1


def _extract_lat_lon_alt(loc) -> Optional[tuple[float, float, float]]:
   if loc is None:
      return None

   # dataclass/object style
   if hasattr(loc, "latitude") and hasattr(loc, "longitude"):
      lat = float(getattr(loc, "latitude"))
      lon = float(getattr(loc, "longitude"))
      alt = float(getattr(loc, "altitude", 0.0) or 0.0)
      return (lat, lon, alt)

   # dict style
   if isinstance(loc, dict):
      if "latitude" in loc and "longitude" in loc:
         lat = float(loc["latitude"])
         lon = float(loc["longitude"])
         alt = float(loc.get("altitude", 0.0) or 0.0)
         return (lat, lon, alt)

   return None


def cmd_home(client: BlueLinky, cfg_data: dict, args: argparse.Namespace) -> int:
   home = cfg_data.get("home")
   if not home:
      print(f"No Home location set")
      return 0

   try:
      lat = float(home[0])
      lon = float(home[1])
      alt = float(home[2]) if len(home) > 2 and home[2] is not None else 0.0
      print(f"Home location: LAT {lat}, LON {lon}, ALT {alt}")
      return 0
   except Exception:
      print(f"Home location: {home!r}")
      return 0


def cmd_home_set(client: BlueLinky, vehicle, cfg_data: dict, args: argparse.Namespace) -> int:
   loc = vehicle.location()
   coords = _extract_lat_lon_alt(loc)
   if coords is None:
      print("Could not read vehicle location; Home not updated")
      return 1

   lat, lon, alt = coords
   cfg_data["home"] = [lat, lon, alt]

   cfg_path = resolve_config_path(args.config)
   save_config(cfg_path, cfg_data)

   print(f"Set Home to: LAT {lat}, LON {lon}, ALT {alt}")
   print(f"Wrote: {cfg_path}")
   return 0


def cmd_locate(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   res = vehicle.location()
   print(f"Current location: LAT {res.latitude}, LON {res.longitude}, ALT {res.altitude}, {res.heading}°")

   if client.config.home:
      home = client.config.home
      dist_km = haversine_km(
         res.latitude, res.longitude,
         home.latitude, home.longitude,
      )
      print(f"Home location: LAT {home.latitude}, LON {home.longitude}, ALT {home.altitude}")
      if dist_km < 1:
         print(f"Distance from home: {(100*dist_km):.0f} m")
      else:
         print(f"Distance from home: {dist_km:.2f} km")
   return 0


def cmd_list(client: BlueLinky, args: argparse.Namespace) -> int:
   vehicles = client.getVehicles()
   if not vehicles:
      print("No vehicles found")
      return 1
   # Convert each vehicle's registration options to a dict for JSON serialization
   try:
      data = [asdict(v.vehicleConfig) for v in vehicles]
   except TypeError:
      # If asdict fails (unlikely), fall back to a simplified representation
      data = []
      for v in vehicles:
         name: Optional[str] = None
         # Some vehicles may not implement nickname/name helpers
         if hasattr(v, "nickname"):
            try:
               name = v.nickname()
            except Exception:
               name = None
         if not name and hasattr(v, "name"):
            try:
               name = v.name()
            except Exception:
               name = None
         vin: Optional[str] = None
         if hasattr(v, "vin"):
            try:
               vin = v.vin()
            except Exception:
               vin = None
         data.append({"name": name, "vin": vin})
   # Print as JSON for consistency with other commands
   print(json.dumps(data, indent=2, default=str))
   return 0


def build_parser() -> argparse.ArgumentParser:
   parser = argparse.ArgumentParser(
      prog="bluelinky",
      description="BlueLinky Python CLI for Hyundai/Kia vehicles",
   )
   parser.add_argument(
      "--config",
      "-c",
      help="Path to config JSON (otherwise use BLUELINKY_CONFIG or default locations)",
   )
   parser.add_argument(
      "--debug",
      "-d",
      action="store_true",
      help="Enable debug logging",
   )

   sub = parser.add_subparsers(dest="command", required=True)

   _list       = sub.add_parser("list", help="List all vehicles.")
   _status     = sub.add_parser("status", help="Show vehicle status.")
   _lock       = sub.add_parser("lock", help="Lock the vehicle.")
   _unlock     = sub.add_parser("unlock", help="Unlock the vehicle.")
   _horn       = sub.add_parser("horn", help="Honk the horn.")
   _flash      = sub.add_parser("flash", help="Flash the lights.")
   _locate     = sub.add_parser("locate", help="Show last known vehicle location.")
   _home       = sub.add_parser("home", help="Show the saved (Home) vehicle location.")
   _home_sub   = _home.add_subparsers(dest="home_command", required=False)
   _home_set   = _home_sub.add_parser("set", help="Set the vehicle's current location as the saved (Home) location.")
   _start      = sub.add_parser("start", help="Remote start with optional climate settings.")
   _start.add_argument("--temp", type=_parse_temperature_arg, help="Target temperature (e.g. 25C or 77F)")
   _start.add_argument("--time", type=_parse_time_arg, help="Ignition duration in minutes (1-30)")
   _start.add_argument("--heat", type=_parse_heat_arg, help="Enable heated features (yes/on/true/all/defrost)")

   return parser


def main(argv: Optional[list[str]] = None) -> int:
   parser = build_parser()
   args = parser.parse_args(argv)

   logging.basicConfig(
      level=logging.DEBUG if args.debug else logging.INFO,
      format="%(asctime)s %(levelname)s %(name)s: %(message)s",
   )

   cfg_data = load_config(args.config)
   client = make_client(cfg_data)

   cmd = args.command

   print(f"Attempting to run '{cmd}' command...")

   # Thes commands do not require selecting a specific vehicle
   if cmd == "list":
      return cmd_list(client, args)
   if cmd == "home":
      if getattr(args, "home_command", None) == "set":
         vehicle = pick_vehicle(client, cfg_data)
         return cmd_home_set(client, vehicle, cfg_data, args)
      return cmd_home(client, cfg_data, args)

   # For other commands we need a specific vehicle
   vehicle = pick_vehicle(client, cfg_data)

   if cmd == "status":
      return cmd_status(client, vehicle, args)
   if cmd == "lock":
      return cmd_lock(client, vehicle, args)
   if cmd == "unlock":
      return cmd_unlock(client, vehicle, args)
   if cmd == "horn":
      return cmd_horn(client, vehicle, args)
   if cmd == "flash":
      return cmd_flash(client, vehicle, args)
   if cmd == "locate":
      return cmd_locate(client, vehicle, args)
   if cmd == "start":
      return cmd_start(client, vehicle, args)

   parser.error(f"Unknown command: {cmd!r}")
   return 2


if __name__ == "__main__":
   raise SystemExit(main())
