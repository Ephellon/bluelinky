from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, TypedDict

import requests

from bluelinky.constants.china import ChineseBrandEnvironment


Code = str


class _LoginUser(TypedDict):
   username: str
   password: str


class _LoginOptions(TypedDict, total=False):
   cookieJar: "CookieJar"


class AuthStrategy(Protocol):
   @property
   def name(self) -> str:
      ...

   def login(
      self,
      user: _LoginUser,
      options: Optional[_LoginOptions] = None
   ) -> dict:
      ...


@dataclass
class CookieJar:
   session: requests.Session


def initSession(
   environment: ChineseBrandEnvironment,
   cookies: Optional[CookieJar] = None
) -> CookieJar:
   cookieJar = cookies or CookieJar(session=requests.Session())

   cookieJar.session.get(environment.endpoints.session)

   cookieJar.session.post(
      environment.endpoints.language,
      data='{"lang":"zh"}'
   )

   return cookieJar