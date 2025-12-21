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
      return min(max(value, 61), 83)
   return min(max(value, 16), 28)


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
      clamped = min(max(clamped, 61), 83)
   else:
      clamped = min(max(clamped, 16), 28)

   return clamped, unit


def _parse_time_arg(value: str) -> int:
   try:
      minutes = int(value)
   except ValueError as exc:
      raise argparse.ArgumentTypeError(f"invalid time value: {value!r}") from exc

   return min(max(minutes, 1), 30)


def _parse_heat_arg(value: str) -> str:
   normalized = str(value).strip().lower()
   if normalized in ("yes", "on", "true", "1"):
      return "on"
   if normalized in ("all"):
      return "all"
   if normalized in ("defrost"):
      return "defrost"
   if normalized in ("no", "off", "false", "0"):
      return "off"

   raise argparse.ArgumentTypeError("--heat must be one of: yes, on, true, 1, all, defrost")


def _parse_charge_limit(value: str) -> int:
   try:
      percent = int(value)
   except ValueError as exc:
      raise argparse.ArgumentTypeError(f"invalid charge limit: {value!r}") from exc

   if percent < 50 or percent > 100:
      raise argparse.ArgumentTypeError("--max must be between 50 and 100 (inclusive)")

   return percent


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


def _status_source_from_arg(value: str) -> str:
   normalized = (value or "parsed").strip().lower()
   if normalized in ("parsed", "full", "cached"):
      return normalized
   raise argparse.ArgumentTypeError("--from must be one of: parsed, full, cached")


def cmd_status(client, vehicle, args):
   source = getattr(args, "from", "parsed")

   try:
      if source == "parsed":
         status = vehicle.status(VehicleStatusOptions(refresh=True, parsed=True))
      elif source == "full":
         status = vehicle.fullStatus(VehicleStatusOptions(refresh=True, parsed=False))
      else:
         status = vehicle.status(VehicleStatusOptions(refresh=False, parsed=True))
   except Exception as exc:
      print(str(exc))
      return 1

   if status is None:
      print("No status returned.")
      return 1

   try:
      data = asdict(status)
   except TypeError:
      data = status

   print(json.dumps(data, indent=4, default=str))
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


def cmd_odometer(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   try:
      odometer = vehicle.odometer()
      if odometer is None:
         print("No odometer returned.")
         return 1

      try:
         data = asdict(odometer)
      except TypeError:
         data = odometer

      print(json.dumps(data, indent=4, default=str))
      return 0
   except Exception as exc:
      print(str(exc))
      return 1


def _ev_drive_history(client, vehicle):
   if hasattr(vehicle, "driveHistory"):
      return vehicle.driveHistory()
   if hasattr(vehicle, "drive_history"):
      return vehicle.drive_history()

   if hasattr(client, "driveHistory"):
      return client.driveHistory(vehicle)
   if hasattr(client, "drive_history"):
      return client.drive_history(vehicle)

   controller = getattr(client, "controller", None)
   if controller and hasattr(controller, "driveHistory"):
      return controller.driveHistory(vehicle)
   if controller and hasattr(controller, "drive_history"):
      return controller.drive_history(vehicle)

   return None


def _ev_charge_targets(client, vehicle):
   if hasattr(vehicle, "getChargeTargets"):
      return vehicle.getChargeTargets()
   if hasattr(vehicle, "get_charge_targets"):
      return vehicle.get_charge_targets()

   if hasattr(client, "getChargeTargets"):
      return client.getChargeTargets(vehicle)
   if hasattr(client, "get_charge_targets"):
      return client.get_charge_targets(vehicle)

   controller = getattr(client, "controller", None)
   if controller and hasattr(controller, "getChargeTargets"):
      return controller.getChargeTargets(vehicle)
   if controller and hasattr(controller, "get_charge_targets"):
      return controller.get_charge_targets(vehicle)

   return None


def _call_if_compatible(obj, name: str, args: tuple, kwargs: dict):
   if obj is None or not hasattr(obj, name):
      return False, None

   fn = getattr(obj, name)
   try:
      return True, fn(*args, **kwargs)
   except TypeError:
      return False, None


def _ev_set_charge_limits(client, vehicle, percent: int):
   attempts = [
      (vehicle, "setChargeLimits", (), {"max": percent}),
      (vehicle, "setChargeLimit", (), {"max": percent}),
      (vehicle, "set_charge_limits", (), {"max": percent}),
      (vehicle, "set_charge_limit", (), {"max": percent}),
      (client, "setChargeLimits", (vehicle, percent), {}),
      (client, "setChargeLimits", (vehicle,), {"max": percent}),
      (client, "setChargeLimit", (vehicle, percent), {}),
      (client, "setChargeLimit", (vehicle,), {"max": percent}),
      (client, "set_charge_limits", (vehicle, percent), {}),
      (client, "set_charge_limits", (vehicle,), {"max": percent}),
      (client, "set_charge_limit", (vehicle, percent), {}),
      (client, "set_charge_limit", (vehicle,), {"max": percent}),
   ]

   controller = getattr(client, "controller", None)
   attempts.extend([
      (controller, "setChargeLimits", (vehicle, percent), {}),
      (controller, "setChargeLimits", (vehicle,), {"max": percent}),
      (controller, "setChargeLimit", (vehicle, percent), {}),
      (controller, "setChargeLimit", (vehicle,), {"max": percent}),
      (controller, "set_charge_limits", (vehicle, percent), {}),
      (controller, "set_charge_limits", (vehicle,), {"max": percent}),
      (controller, "set_charge_limit", (vehicle, percent), {}),
      (controller, "set_charge_limit", (vehicle,), {"max": percent}),
   ])

   for obj, name, args, kwargs in attempts:
      ok, res = _call_if_compatible(obj, name, args, kwargs)
      if ok:
         return res

   return None


def cmd_charge(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   try:
      if getattr(args, "targets", False):
         res = _ev_charge_targets(client, vehicle)
         if res is None:
            print("EV charge targets are not implemented in this port yet.")
            return 1
         print(json.dumps(res, indent=4, default=str))
         return 0

      if getattr(args, "max", None) is not None:
         res = _ev_set_charge_limits(client, vehicle, args.max)
         if res is None:
            print("EV charge limits are not implemented in this port yet.")
            return 1
         print(json.dumps(res, indent=4, default=str))
         return 0

      res = vehicle.startCharge()
      print(res)
      return 0
   except Exception as exc:
      print(str(exc))
      return 1


def cmd_report(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   try:
      report = vehicle.monthlyReport()
      print(json.dumps(report, indent=4, default=str))
      return 0
   except Exception as exc:
      print(str(exc))
      return 1


def cmd_history(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   try:
      if getattr(args, "scope", None) == "all":
         history = _ev_drive_history(client, vehicle)
         if history is None:
            print("EV drive history is not implemented in this port yet.")
            return 1
      else:
         history = vehicle.tripInfo()
      print(json.dumps(history, indent=4, default=str))
      return 0
   except Exception as exc:
      print(str(exc))
      return 1


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

      target_unit = _target_unit_for_vehicle(vehicle)
      highest_temp = 83 if target_unit == "F" else 28
      default_temp = 72 if target_unit == "F" else 22
      lowest_temp  = 61 if target_unit == "F" else 16
      hvac_on = bool((getattr(args, "temp", None) is not None) or heat_on or defrost_on)

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
         # If user didn't specify temp:
         #     heat_on: use the highest temperature
         #     defrost_on: use default temperature to avoid "heating" intent while keeping API happy
         if heat_on:
            temp_value = highest_temp
         elif defrost_on:
            temp_value = default_temp

      duration = getattr(args, "time", None)
      if duration is None:
         duration = 10

      start_options = VehicleStartOptions(
         hvac=hvac_on,
         duration=duration,
         temperature=temp_value if temp_value is not None else default_temp,
         defrost=defrost_on,
         heatedFeatures=heat_on,
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


def cmd_stop(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   try:
      log.info("Stopping vehicle...")
      res = vehicle.stop()
      print("Stop command sent:", res)
      return 0
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
   loc = vehicle.location()

   try:
      data = asdict(loc)
   except TypeError:
      data = loc

   print(json.dumps(data, indent=4, default=str))
   return 0


def format_heading(deg: float) -> str:
   directions = [
      "N", "NE",
      "E", "SE",
      "S", "SW",
      "W", "NW",
   ]

   deg = deg % 360
   idx = int((deg + 22.5) / 45) % 8
   return f"{int(round(deg))}°{directions[idx]}"


def cmd_locate_offset(client: BlueLinky, vehicle, args: argparse.Namespace) -> int:
   res = vehicle.location()
   lat = res.latitude
   lon = res.longitude
   alt = res.altitude
   head = res.heading
   print(f"Current location:\n\tLAT {lat}, LON {lon}, ALT {alt}, {format_heading(head)}")

   if client.config.home:
      home = client.config.home
      dist_km = haversine_km(
         res.latitude, res.longitude,
         home.latitude, home.longitude,
      )
      print(f"Home location:\n\tLAT {home.latitude}, LON {home.longitude}, ALT {home.altitude}")
      if dist_km < 1:
         print(f"Distance from home:\n\t{(100*dist_km):.0f} m")
      else:
         print(f"Distance from home:\n\t{dist_km:.2f} km")
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
   print(json.dumps(data, indent=4, default=str))
   return 0


def _present(value):
   return value if value is not None else "<NOT SET>"


def _present_secret(value):
   return "<PROVIDED>" if value else "<MISSING>"


def print_config_summary(cfg_path: Path, cfg_data: dict, args):
   print("\n--- BlueLinky Configuration ---")
   print(f"Config file: {cfg_path}")
   print(f"Region: {_present(cfg_data.get('region'))}")
   print(f"Brand: {_present(cfg_data.get('brand'))}")
   print(f"Username: {_present(cfg_data.get('username'))}")
   print(f"Password: {_present_secret(cfg_data.get('password'))}")
   print(f"PIN: {_present_secret(cfg_data.get('pin'))}")
   print(f"VIN: {_present(cfg_data.get('vin'))}")
   print(f"Vehicle ID: {_present(cfg_data.get('vehicleId'))}")
   print(f"Home: {_present(cfg_data.get('home'))}")
   print(f"Debug: {'on' if args.debug else 'off'}")
   print("-------------------------------\n")


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

   sub = parser.add_subparsers(dest="command", required=False)

   _whoami     = sub.add_parser("whoami", help="Prints the currently loaded configuration summary.")
   _list       = sub.add_parser("list", help="List all vehicles.")
   _status     = sub.add_parser("status", help="Show vehicle status.")
   _status.add_argument("--from", dest="from", type=_status_source_from_arg, default="parsed", help="Status source: parsed (default), full, cached")
   _lock       = sub.add_parser("lock", help="Lock the vehicle.")
   _unlock     = sub.add_parser("unlock", help="Unlock the vehicle.")
   _horn       = sub.add_parser("horn", help="Honk the horn.")
   _flash      = sub.add_parser("flash", help="Flash the lights.")
   _locate     = sub.add_parser("locate", help="Show last known vehicle location.")
   _locate_sub = _locate.add_subparsers(dest="locate_command", required=False)
   _locate_set = _locate_sub.add_parser("offset", help="Show location offset from configured home position.")
   _odometer   = sub.add_parser("odometer", help="Show the vehicle odometer.")
   _home       = sub.add_parser("home", help="Show the saved (Home) vehicle location.")
   _home_sub   = _home.add_subparsers(dest="home_command", required=False)
   _home_set   = _home_sub.add_parser("set", help="Set the vehicle's current location as the saved (Home) location.")
   _start      = sub.add_parser("start", help="Remote start (turn on) with optional climate settings.")
   _start.add_argument("--temp", type=_parse_temperature_arg, help="Target temperature (e.g. 25C or 77F)")
   _start.add_argument("--time", type=_parse_time_arg, help="Ignition duration in minutes (1-30)")
   _start.add_argument("--heat", type=_parse_heat_arg, help="Enable heated features (truthy/all/defrost/falsy)")
   _stop       = sub.add_parser("stop", help="Remote stop (turn off).")
   _charge     = sub.add_parser("charge", help="Start charging the vehicle or manage EV charge settings.")
   charge_mode = _charge.add_mutually_exclusive_group()
   charge_mode.add_argument("--targets", action="store_true", help="Get EV charge targets (if supported).")
   charge_mode.add_argument("--max", type=_parse_charge_limit, help="Set EV charge limit (50-100%).")
   _report     = sub.add_parser("report", help="Get the monthly report.")
   _history    = sub.add_parser("history", help="Get trip/usage history.")
   _history.add_argument("scope", nargs="?", choices=["all"], help="Use 'all' for EV drive history (if supported).")

   return parser


def main(argv: Optional[list[str]] = None) -> int:
   parser = build_parser()
   args = parser.parse_args(argv)

   cfg_path = resolve_config_path(args.config)
   cfg_data = load_config(args.config)

   if args.command is None:
      print_config_summary(cfg_path, cfg_data, args)
      parser.error("the following arguments are required: command")

   logging.basicConfig(
      level=logging.DEBUG if args.debug else logging.INFO,
      format="%(asctime)s %(levelname)s %(name)s: %(message)s",
   )

   cfg_data = load_config(args.config)
   client = make_client(cfg_data)

   cmd = args.command

   print(f"Attempting to run '{cmd}' command...")

   # Thes commands do not require selecting a specific vehicle
   if cmd == "whoami":
      return print_config_summary(cfg_path, cfg_data, args)
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
      if getattr(args, "locate_command", None) == "offset":
         return cmd_locate_offset(client, vehicle, args)
      return cmd_locate(client, vehicle, args)
   if cmd == "odometer":
      return cmd_odometer(client, vehicle, args)
   if cmd == "start":
      return cmd_start(client, vehicle, args)
   if cmd == "stop":
      return cmd_stop(client, vehicle, args)
   if cmd == "charge":
      return cmd_charge(client, vehicle, args)
   if cmd == "report":
      return cmd_report(client, vehicle, args)
   if cmd == "history":
      return cmd_history(client, vehicle, args)

   parser.error(f"Unknown command: {cmd!r}")
   return 2


if __name__ == "__main__":
   raise SystemExit(main())
