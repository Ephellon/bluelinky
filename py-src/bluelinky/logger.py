from __future__ import annotations

import logging

logger = logging.getLogger("bluelinky")
if not logger.handlers:
   handler = logging.StreamHandler()
   formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
   handler.setFormatter(formatter)
   logger.addHandler(handler)
logger.setLevel(logging.INFO)

__all__ = ["logger"]
