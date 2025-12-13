"""Base controller definition."""
from __future__ import annotations

import time
from typing import List

import requests

from ..interfaces import BlueLinkyConfig, Session
from ..vehicles.base import Vehicle


class SessionController:
    """Base session controller used by regional implementations."""

    def __init__(self, user_config: BlueLinkyConfig) -> None:
        self.user_config = user_config
        self.session = Session()
        self.http = requests.Session()

    def login(self) -> str:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def logout(self) -> str:
        return "OK"

    def get_vehicles(self) -> List[Vehicle]:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def refresh_access_token(self) -> str:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def token_expired(self) -> bool:
        if not self.session.token_expires_at:
            return True
        return time.time() >= self.session.token_expires_at - 10
