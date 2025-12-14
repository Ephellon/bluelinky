"""
Convenience re‑exports for authentication strategy modules.

Any module inside this package will be imported and its public names (those
not starting with an underscore) will be added to this package’s namespace.
If a module defines an `__all__` list, only those names are exported.

This allows you to write, for example:

   from bluelinky.controllers.authStrategies import AmericanAuthStrategy

…without having to know the specific module where the class lives.
"""

from importlib import import_module as _import_module
import pkgutil as _pkgutil

__all__ = []

for _mod_info in _pkgutil.iter_modules(__path__):  # type: ignore[name-defined]
   _mod = _import_module(f"{__name__}.{_mod_info.name}")

   if hasattr(_mod, "__all__") and isinstance(_mod.__all__, (list, tuple)):
      _names = list(_mod.__all__)
   else:
      _names = [n for n in dir(_mod) if not n.startswith("_")]

   for _name in _names:
      globals()[_name] = getattr(_mod, _name)
      if _name not in __all__:
         __all__.append(_name)
