import json
import logging
import os
from datetime import datetime
from typing import Any


_DEFAULT_LEVEL = os.environ.get("LOG_LEVEL", "info").lower()

_LEVEL_MAP = {
   "error": logging.ERROR,
   "warn": logging.WARNING,
   "warning": logging.WARNING,
   "info": logging.INFO,
   "verbose": logging.INFO,
   "debug": logging.DEBUG,
   "silly": logging.DEBUG,
}


class _JsonLikeFormatter(logging.Formatter):
   def format(self, record: logging.LogRecord) -> str:
      ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
      level = record.levelname.lower()

      message: Any = record.msg
      if isinstance(message, (dict, list, tuple)):
         message = json.dumps(message, indent=2, ensure_ascii=False)

      if record.args:
         try:
            message = str(message) % record.args
         except Exception:
            message = f"{message} {record.args}"

      return f"[{ts}] {level}: {message}"


logger = logging.getLogger("bluelinky")
logger.setLevel(_LEVEL_MAP.get(_DEFAULT_LEVEL, logging.INFO))
logger.propagate = False

if not logger.handlers:
   handler = logging.StreamHandler()
   handler.setLevel(logger.level)
   handler.setFormatter(_JsonLikeFormatter())
   logger.addHandler(handler)