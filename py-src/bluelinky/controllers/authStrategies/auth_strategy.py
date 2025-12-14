from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, TypedDict

import requests

from ...constants.europe import EuropeanBrandEnvironment

try:
   from requests.cookies import RequestsCookieJar as CookieJar
except Exception:  # pragma: no cover
   CookieJar = object  # type: ignore[misc,assignment]


Code = str


class _UserDict(TypedDict):
   username: str
   password: str


class _LoginOptions(TypedDict, total=False):
   cookieJar: "CookieJar"


class _LoginResult(TypedDict):
   code: Code
   cookies: "CookieJar"


class AuthStrategy(Protocol):
   @property
   def name(self) -> str: ...

   def login(self, user: _UserDict, options: Optional[_LoginOptions] = None) -> _LoginResult: ...


def initSession(environment: EuropeanBrandEnvironment, cookies: Optional["CookieJar"] = None) -> "CookieJar":
   cookie_jar: CookieJar
   if cookies is None:
      cookie_jar = requests.cookies.RequestsCookieJar()
   else:
      cookie_jar = cookies

   requests.get(environment.endpoints.session, cookies=cookie_jar)
   # Language endpoint now requires authentication, so we skip it
   # Language will be set in the authentication URL instead
   return cookie_jar