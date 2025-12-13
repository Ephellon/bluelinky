"""Lightweight logger wrapper for the Python port."""
from __future__ import annotations

import logging
import os


def get_logger(name: str = "bluelinky") -> logging.Logger:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, level, logging.INFO))
    return logging.getLogger(name)


logger = get_logger()
