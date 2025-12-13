import logging
import os


def _build_logger() -> logging.Logger:
   level_name = os.getenv("LOG_LEVEL", "INFO").upper()
   logging.basicConfig(
      level=getattr(logging, level_name, logging.INFO),
      format="[%(asctime)s] %(levelname)s: %(message)s",
      datefmt="%Y-%m-%d %H:%M:%S",
   )
   return logging.getLogger("bluelinky")


logger = _build_logger()

