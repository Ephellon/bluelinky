from bluelinky.constants import REGIONS
from bluelinky.vehicles.vehicle import Vehicle


class CanadianVehicle(Vehicle):
   region = REGIONS.CA

   def status(self, input):
      raise NotImplementedError

   def fullStatus(self, input):
      raise NotImplementedError

   def unlock(self):
      raise NotImplementedError

   def lock(self):
      raise NotImplementedError

   def start(self, config):
      raise NotImplementedError

   def stop(self):
      raise NotImplementedError

   def location(self):
      raise NotImplementedError

   def odometer(self):
      raise NotImplementedError

