from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypeVar, Union, cast

from ..constants import (
   DEFAULT_VEHICLE_STATUS_OPTIONS,
   POSSIBLE_CHARGE_LIMIT_VALUES,
   REGIONS,
   ChargeTarget,
)
from ..interfaces.common_interfaces import (
   DeepPartial,
   EVChargeModeTypes,
   EVPlugTypes,
   FullVehicleStatus,
   RawVehicleStatus,
   VehicleDayTrip,
   VehicleLocation,
   VehicleMonthTrip,
   VehicleMonthlyReport,
   VehicleOdometer,
   VehicleRegisterOptions,
   VehicleStartOptions,
   VehicleStatus,
   VehicleStatusOptions,
   VehicleTargetSOC,
)
from ..interfaces.chinese_interfaces import (
   CNDatedDriveHistory,
   CNDriveHistory,
   CNPOIInformation,
   historyDrivingPeriod,
)
from ..logger import logger
from ..tools.common_tools import ManagedBluelinkyError, manageBluelinkyError
from ..util import addMinutes, celciusToTempCode, parseDate, tempCodeToCelsius
from .vehicle import Vehicle

if TYPE_CHECKING:  # pragma: no cover - type checking only
   from ..controllers.chinese_controller import ChineseController

TResp = TypeVar("TResp", bound=Dict[str, Any])


@dataclass
class _HttpResponse:
   statusCode: int
   headers: Dict[str, Any]
   body: Any


class ChineseVehicle(Vehicle):
   region = REGIONS.CN

   serverRates: Dict[str, Any] = {
      "max": -1,
      "current": -1,
   }

   def __init__(self, vehicleConfig: VehicleRegisterOptions, controller: ChineseController):
      super().__init__(vehicleConfig, controller)
      self.vehicleConfig = vehicleConfig
      self.controller = controller
      logger.debug(f"CN Vehicle {self.vehicleConfig.id} created")

   def start(self, config: VehicleStartOptions) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/engine",
               body={
                  "action": "start",
                  "hvacType": 1,
                  "options": {
                     "defrost": config.defrost,
                     "heating1": 1 if getattr(config, "heatedFeatures", None) else 0,
                  },
                  "tempCode": celciusToTempCode(REGIONS.CN, config.temperature),
                  "unit": config.unit,
               },
            )
         )
         logger.info(f"Climate started for vehicle {self.vehicleConfig.id}")
         return cast(str, response.body)
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.start")

   def stop(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/engine",
               body={
                  "action": "stop",
                  "hvacType": 0,
                  "options": {
                     "defrost": True,
                     "heating1": 1,
                  },
                  "tempCode": "10H",
                  "unit": "C",
               },
            )
         )
         logger.info(f"Climate stopped for vehicle {self.vehicleConfig.id}")
         return cast(str, response.body)
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.stop")

   def lock(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/door",
               body={
                  "action": "close",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )
         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Vehicle {self.vehicleConfig.id} locked")
            return "Lock successful"
         return "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.lock")

   def unlock(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/door",
               body={
                  "action": "open",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Vehicle {self.vehicleConfig.id} unlocked")
            return "Unlock successful"

         return "Something went wrong!"
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.unlock")

   def fullStatus(self, input: VehicleStatusOptions) -> Optional[FullVehicleStatus]:
      statusConfig: Dict[str, Any] = {**DEFAULT_VEHICLE_STATUS_OPTIONS, **(input or {})}

      http = self.controller.getVehicleHttpService()

      try:
         cachedResponse = self._updateRates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status/latest")
         )

         fullStatus = cachedResponse.body["resMsg"]["status"]

         if statusConfig.get("refresh"):
            statusResponse = self._updateRates(
               http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status")
            )
            fullStatus["vehicleStatus"] = statusResponse.body["resMsg"]["status"]

            locationResponse = self._updateRates(
               http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location")
            )
            fullStatus["vehicleLocation"] = locationResponse.body["resMsg"]["coord"]

         self._fullStatus = fullStatus
         return cast(Optional[FullVehicleStatus], self._fullStatus)
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.fullStatus")

   def status(self, input: VehicleStatusOptions | None = None) -> Optional[Union[VehicleStatus, RawVehicleStatus]]:
      if input is None:
         input = VehicleStatusOptions(refresh=True, parsed=True)

      statusConfig: Dict[str, Any] = {**DEFAULT_VEHICLE_STATUS_OPTIONS, **(input or {})}

      http = self.controller.getVehicleHttpService()

      try:
         cacheString = "" if statusConfig.get("refresh") else "/latest"

         response = self._updateRates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status{cacheString}")
         )

         vehicleStatus = response.body["resMsg"]["status"]

         def _get(dct: Any, *path: str) -> Any:
            cur = dct
            for p in path:
               if cur is None:
                  return None
               if isinstance(cur, dict):
                  cur = cur.get(p)
               else:
                  cur = getattr(cur, p, None)
            return cur

         parsedStatus: Dict[str, Any] = {
            "chassis": {
               "hoodOpen": _get(vehicleStatus, "hoodOpen"),
               "trunkOpen": _get(vehicleStatus, "trunkOpen"),
               "locked": _get(vehicleStatus, "doorLock"),
               "openDoors": {
                  "frontRight": bool(_get(vehicleStatus, "doorOpen", "frontRight")),
                  "frontLeft": bool(_get(vehicleStatus, "doorOpen", "frontLeft")),
                  "backLeft": bool(_get(vehicleStatus, "doorOpen", "backLeft")),
                  "backRight": bool(_get(vehicleStatus, "doorOpen", "backRight")),
               },
               "tirePressureWarningLamp": {
                  "rearLeft": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampRL")),
                  "frontLeft": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampFL")),
                  "frontRight": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampFR")),
                  "rearRight": bool(_get(vehicleStatus, "tirePressureLamp", "tirePressureLampRR")),
                  "all": bool(
                     _get(vehicleStatus, "tirePressureLamp", "tirePressureWarningLampAll")
                  ),
               },
            },
            "climate": {
               "active": _get(vehicleStatus, "airCtrlOn"),
               "steeringwheelHeat": bool(_get(vehicleStatus, "steerWheelHeat")),
               "sideMirrorHeat": False,
               "rearWindowHeat": bool(_get(vehicleStatus, "sideBackWindowHeat")),
               "defrost": _get(vehicleStatus, "defrost"),
               "temperatureSetpoint": tempCodeToCelsius(
                  REGIONS.EU, _get(vehicleStatus, "airTemp", "value")
               ),
               "temperatureUnit": _get(vehicleStatus, "airTemp", "unit"),
            },
            "engine": {
               "ignition": _get(vehicleStatus, "engine"),
               "accessory": _get(vehicleStatus, "acc"),
               "rangeGas": (
                  _get(
                     vehicleStatus,
                     "evStatus",
                     "drvDistance",
                     "0",
                     "rangeByFuel",
                     "gasModeRange",
                     "value",
                  )
                  if False
                  else None
               ),
               "range": _get(
                  vehicleStatus,
                  "evStatus",
                  "drvDistance",
                  0,
                  "rangeByFuel",
                  "totalAvailableRange",
                  "value",
               ),
               "rangeEV": _get(
                  vehicleStatus, "evStatus", "drvDistance", 0, "rangeByFuel", "evModeRange", "value"
               ),
               "plugedTo": _get(vehicleStatus, "evStatus", "batteryPlugin") or EVPlugTypes.UNPLUGED,
               "charging": _get(vehicleStatus, "evStatus", "batteryCharge"),
               "estimatedCurrentChargeDuration": _get(
                  vehicleStatus, "evStatus", "remainTime2", "atc", "value"
               ),
               "estimatedFastChargeDuration": _get(
                  vehicleStatus, "evStatus", "remainTime2", "etc1", "value"
               ),
               "estimatedPortableChargeDuration": _get(
                  vehicleStatus, "evStatus", "remainTime2", "etc2", "value"
               ),
               "estimatedStationChargeDuration": _get(
                  vehicleStatus, "evStatus", "remainTime2", "etc3", "value"
               ),
               "batteryCharge12v": _get(vehicleStatus, "battery", "batSoc"),
               "batteryChargeHV": _get(vehicleStatus, "evStatus", "batteryStatus"),
            },
            "lastupdate": parseDate(_get(vehicleStatus, "time")) if _get(vehicleStatus, "time") else None,
         }

         # Faithful nullish-coalescing behavior for rangeGas.
         range_gas = _get(
            vehicleStatus, "evStatus", "drvDistance", 0, "rangeByFuel", "gasModeRange", "value"
         )
         if range_gas is None:
            range_gas = _get(vehicleStatus, "dte", "value")
         parsedStatus["engine"]["rangeGas"] = range_gas

         if not parsedStatus["engine"].get("range"):
            if parsedStatus["engine"].get("rangeEV") or parsedStatus["engine"].get("rangeGas"):
               parsedStatus["engine"]["range"] = (parsedStatus["engine"].get("rangeEV") or 0) + (
                  parsedStatus["engine"].get("rangeGas") or 0
               )

         self._status = parsedStatus if statusConfig.get("parsed") else vehicleStatus
         return cast(Optional[Union[VehicleStatus, RawVehicleStatus]], self._status)
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.status")

   def odometer(self) -> Optional[VehicleOdometer]:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/status/latest")
         )
         self._odometer = cast(VehicleOdometer, response.body["resMsg"]["status"]["odometer"])
         return cast(Optional[VehicleOdometer], self._odometer)
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.odometer")

   def location(self) -> VehicleLocation:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location"))

         resMsg = response.body.get("resMsg") if isinstance(response.body, dict) else None
         data = (resMsg.get("gpsDetail") if isinstance(resMsg, dict) else None) or resMsg

         coord = data.get("coord") if isinstance(data, dict) else None
         speed = data.get("speed") if isinstance(data, dict) else None

         self._location = {
            "latitude": (coord or {}).get("lat") if isinstance(coord, dict) else None,
            "longitude": (coord or {}).get("lon") if isinstance(coord, dict) else None,
            "altitude": (coord or {}).get("alt") if isinstance(coord, dict) else None,
            "speed": {
               "unit": (speed or {}).get("unit") if isinstance(speed, dict) else None,
               "value": (speed or {}).get("value") if isinstance(speed, dict) else None,
            },
            "heading": data.get("head") if isinstance(data, dict) else None,
         }

         return cast(VehicleLocation, self._location)
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.location")

   def startCharge(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
               body={
                  "action": "start",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Send start charge command to Vehicle {self.vehicleConfig.id}")
            return "Start charge successful"

         raise Exception("Something went wrong!")
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.startCharge")

   def stopCharge(self) -> str:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/control/charge",
               body={
                  "action": "stop",
                  "deviceId": self.controller.session.deviceId,
               },
            )
         )

         if getattr(response, "statusCode", None) == 200:
            logger.debug(f"Send stop charge command to Vehicle {self.vehicleConfig.id}")
            return "Stop charge successful"

         raise Exception("Something went wrong!")
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.stopCharge")

   def monthlyReport(
      self,
      month: Dict[str, int] = None,
   ) -> Optional[DeepPartial[VehicleMonthlyReport]]:
      if month is None:
         now = datetime.now()
         month = {"year": now.year, "month": now.month}

      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/monthlyreport",
               body={
                  "setRptMonth": _toMonthDate(month),
               },
            )
         )
         rawData = (
            response.body.get("resMsg", {}).get("monthlyReport")
            if isinstance(response.body, dict)
            else None
         )
         if rawData:
            driving = rawData.get("driving") if isinstance(rawData, dict) else None
            vehicle_status = rawData.get("vehicleStatus") if isinstance(rawData, dict) else None
            ifo = rawData.get("ifo") if isinstance(rawData, dict) else None

            return cast(
               Optional[DeepPartial[VehicleMonthlyReport]],
               {
                  "start": (ifo or {}).get("mvrMonthStart") if isinstance(ifo, dict) else None,
                  "end": (ifo or {}).get("mvrMonthEnd") if isinstance(ifo, dict) else None,
                  "breakdown": rawData.get("breakdown") if isinstance(rawData, dict) else None,
                  "driving": (
                     {
                        "distance": driving.get("runDistance") if isinstance(driving, dict) else None,
                        "startCount": (
                           driving.get("engineStartCount") if isinstance(driving, dict) else None
                        ),
                        "durations": {
                           "idle": driving.get("engineIdleTime") if isinstance(driving, dict) else None,
                           "drive": driving.get("engineOnTime") if isinstance(driving, dict) else None,
                        },
                     }
                     if driving
                     else None
                  ),
                  "vehicleStatus": (
                     {
                        "tpms": (
                           bool(vehicle_status.get("tpmsSupport"))
                           if isinstance(vehicle_status, dict) and vehicle_status.get("tpmsSupport")
                           else None
                        ),
                        "tirePressure": {
                           "all": (
                              vehicle_status.get("tirePressure", {}).get("tirePressureLampAll") == "1"
                              if isinstance(vehicle_status, dict)
                              and isinstance(vehicle_status.get("tirePressure"), dict)
                              else False
                           )
                        },
                     }
                     if vehicle_status
                     else None
                  ),
               },
            )
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.monthyReports")

   def tripInfo(
      self,
      date: Dict[str, int] = None,
   ) -> Optional[Union[List[DeepPartial[VehicleDayTrip]], DeepPartial[VehicleMonthTrip]]]:
      if date is None:
         now = datetime.now()
         date = {"year": now.year, "month": now.month}

      http = self.controller.getApiHttpService()
      try:
         perDay = bool(date.get("day"))
         response = self._updateRates(
            http.post(
               f"/api/v1/spa/vehicles/{self.vehicleConfig.id}/tripinfo",
               body={
                  "setTripLatest": 10,
                  "setTripMonth": None if perDay else _toMonthDate(date),
                  "setTripDay": _toDayDate(date) if perDay else None,
                  "tripPeriodType": 1 if perDay else 0,
               },
            )
         )

         if not perDay:
            rawData = response.body.get("resMsg") if isinstance(response.body, dict) else None
            tripDayList = rawData.get("tripDayList") if isinstance(rawData, dict) else None
            days = []
            if isinstance(tripDayList, list):
               for day in tripDayList:
                  if isinstance(day, dict):
                     raw = day.get("tripDayInMonth")
                     days.append(
                        {
                           "dayRaw": raw,
                           "date": parseDate(raw) if raw else None,
                           "tripsCount": day.get("tripCntDay"),
                        }
                     )
            return cast(
               DeepPartial[VehicleMonthTrip],
               {
                  "days": days,
                  "durations": {
                     "drive": rawData.get("tripDrvTime") if isinstance(rawData, dict) else None,
                     "idle": rawData.get("tripIdleTime") if isinstance(rawData, dict) else None,
                  },
                  "distance": rawData.get("tripDist") if isinstance(rawData, dict) else None,
                  "speed": {
                     "avg": rawData.get("tripAvgSpeed") if isinstance(rawData, dict) else None,
                     "max": rawData.get("tripMaxSpeed") if isinstance(rawData, dict) else None,
                  },
               },
            )

         rawData = (
            response.body.get("resMsg", {}).get("dayTripList")
            if isinstance(response.body, dict)
            else None
         )
         if rawData and isinstance(rawData, list):
            out: List[DeepPartial[VehicleDayTrip]] = []
            for day in rawData:
               if not isinstance(day, dict):
                  continue
               trip_list = day.get("tripList")
               trips: List[Dict[str, Any]] = []
               if isinstance(trip_list, list):
                  for trip in trip_list:
                     if not isinstance(trip, dict):
                        continue
                     start = parseDate(f"{day.get('tripDay')}{trip.get('tripTime')}")
                     trips.append(
                        {
                           "timeRaw": trip.get("tripTime"),
                           "start": start,
                           "end": addMinutes(start, trip.get("tripDrvTime")),
                           "durations": {
                              "drive": trip.get("tripDrvTime"),
                              "idle": trip.get("tripIdleTime"),
                           },
                           "speed": {
                              "avg": trip.get("tripAvgSpeed"),
                              "max": trip.get("tripMaxSpeed"),
                           },
                           "distance": trip.get("tripDist"),
                        }
                     )
               out.append(
                  {
                     "dayRaw": day.get("tripDay"),
                     "tripsCount": day.get("dayTripCnt"),
                     "distance": day.get("tripDist"),
                     "durations": {
                        "drive": day.get("tripDrvTime"),
                        "idle": day.get("tripIdleTime"),
                     },
                     "speed": {
                        "avg": day.get("tripAvgSpeed"),
                        "max": day.get("tripMaxSpeed"),
                     },
                     "trips": trips,
                  }
               )
            return out

         return None
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.history")

   def driveHistory(
      self, period: historyDrivingPeriod = historyDrivingPeriod.DAY
   ) -> DeepPartial[Dict[str, Any]]:
      http = self.controller.getApiHttpService()
      try:
         response = http.post(
            f"/api/v1/spa/vehicles/{self.vehicleConfig.id}/drvhistory",
            body={
               "periodTarget": period,
            },
         )
         resMsg = response.body.get("resMsg") if isinstance(response.body, dict) else None
         drivingInfo = resMsg.get("drivingInfo") if isinstance(resMsg, dict) else None
         drivingInfoDetail = resMsg.get("drivingInfoDetail") if isinstance(resMsg, dict) else None

         cumulated: Optional[List[DeepPartial[CNDriveHistory]]] = None
         if isinstance(drivingInfo, list):
            cumulated = []
            for line in drivingInfo:
               if not isinstance(line, dict):
                  continue
               cumulated.append(
                  {
                     "period": line.get("drivingPeriod"),
                     "consumption": {
                        "total": line.get("totalPwrCsp"),
                        "engine": line.get("motorPwrCsp"),
                        "climate": line.get("climatePwrCsp"),
                        "devices": line.get("eDPwrCsp"),
                        "battery": line.get("batteryMgPwrCsp"),
                     },
                     "regen": line.get("regenPwr"),
                     "distance": line.get("calculativeOdo"),
                  }
               )

         history: Optional[List[DeepPartial[CNDatedDriveHistory]]] = None
         if isinstance(drivingInfoDetail, list):
            history = []
            for line in drivingInfoDetail:
               if not isinstance(line, dict):
                  continue
               raw_date = line.get("drivingDate")
               history.append(
                  {
                     "period": line.get("drivingPeriod"),
                     "rawDate": raw_date,
                     "date": parseDate(raw_date) if raw_date else None,
                     "consumption": {
                        "total": line.get("totalPwrCsp"),
                        "engine": line.get("motorPwrCsp"),
                        "climate": line.get("climatePwrCsp"),
                        "devices": line.get("eDPwrCsp"),
                        "battery": line.get("batteryMgPwrCsp"),
                     },
                     "regen": line.get("regenPwr"),
                     "distance": line.get("calculativeOdo"),
                  }
               )

         return cast(
            DeepPartial[Dict[str, Any]],
            {
               "cumulated": cumulated,
               "history": history,
            },
         )
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.history")

   def getChargeTargets(self) -> Optional[List[DeepPartial[VehicleTargetSOC]]]:
      http = self.controller.getVehicleHttpService()
      try:
         response = self._updateRates(
            http.get(f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/charge/target")
         )
         rawData = (
            response.body.get("resMsg", {}).get("targetSOClist")
            if isinstance(response.body, dict)
            else None
         )
         if rawData and isinstance(rawData, list):
            out: List[DeepPartial[VehicleTargetSOC]] = []
            for rawSOC in rawData:
               if not isinstance(rawSOC, dict):
                  continue
               drv_distance = rawSOC.get("drvDistance")
               distance_type = drv_distance.get("distanceType") if isinstance(drv_distance, dict) else None
               out.append(
                  {
                     "distance": (
                        distance_type.get("distanceValue") if isinstance(distance_type, dict) else None
                     ),
                     "targetLevel": rawSOC.get("targetSOClevel"),
                     "type": rawSOC.get("plugType"),
                  }
               )
            return out
         return None
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.getChargeTargets")

   def setChargeTargets(self, limits: Dict[str, ChargeTarget]) -> None:
      http = self.controller.getVehicleHttpService()
      if (
         limits.get("fast") not in POSSIBLE_CHARGE_LIMIT_VALUES
         or limits.get("slow") not in POSSIBLE_CHARGE_LIMIT_VALUES
      ):
         raise ManagedBluelinkyError(
            f"Charge target values are limited to {', '.join([str(x) for x in POSSIBLE_CHARGE_LIMIT_VALUES])}"
         )
      try:
         self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/charge/target",
               body={
                  "targetSOClist": [
                     {"plugType": EVChargeModeTypes.FAST, "targetSOClevel": limits.get("fast")},
                     {"plugType": EVChargeModeTypes.SLOW, "targetSOClevel": limits.get("slow")},
                  ],
               },
            )
         )
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.setChargeTargets")

   def setNavigation(self, poiInformations: List[CNPOIInformation]) -> None:
      http = self.controller.getVehicleHttpService()
      try:
         self._updateRates(
            http.post(
               f"/api/v2/spa/vehicles/{self.vehicleConfig.id}/location/routes",
               body={
                  "deviceID": self.controller.session.deviceId,
                  "poiInfoList": poiInformations,
               },
            )
         )
      except Exception as err:
         raise manageBluelinkyError(err, "ChinaVehicle.setNavigation")

   def _updateRates(self, resp: Any) -> Any:
      headers = getattr(resp, "headers", None) or {}
      if isinstance(headers, dict) and headers.get("x-ratelimit-limit") is not None:
         self.serverRates["max"] = int(headers.get("x-ratelimit-limit"))
         self.serverRates["current"] = int(headers.get("x-ratelimit-remaining"))
         if headers.get("x-ratelimit-reset") is not None:
            reset_raw = headers.get("x-ratelimit-reset")
            try:
               self.serverRates["reset"] = datetime.fromtimestamp(int(f"{reset_raw}000") / 1000.0)
            except Exception:
               self.serverRates["reset"] = None
         self.serverRates["updatedAt"] = datetime.now()
      return resp


def _toMonthDate(month: Dict[str, int]) -> str:
   return f"{month['year']}{str(month['month']).zfill(2)}"


def _toDayDate(date: Dict[str, int]) -> str:
   if date.get("day"):
      return f"{_toMonthDate(date)}{str(date['day']).zfill(2)}"
   return _toMonthDate(date)
