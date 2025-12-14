from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypedDict
from urllib.parse import urlparse, parse_qs

import requests

from ...constants.china import ChineseBrandEnvironment
from .china_authStrategy import AuthStrategy, Code, initSession


class _LoginUser(TypedDict):
   username: str
   password: str


class _LoginOptions(TypedDict, total=False):
   cookieJar: object


@dataclass
class ChineseLegacyAuthStrategy(AuthStrategy):
   environment: ChineseBrandEnvironment

   @property
   def name(self) -> str:
      return "ChineseLegacyAuthStrategy"

   def login(
      self,
      user: _LoginUser,
      options: Optional[_LoginOptions] = None
   ) -> dict:
      cookie_jar = initSession(self.environment, (options or {}).get("cookieJar"))

      response = requests.post(
         self.environment.endpoints.login,
         json={
            "email": user["username"],
            "password": user["password"],
         },
         cookies=cookie_jar
      )

      status_code = response.status_code
      try:
         body = response.json()
      except Exception:
         body = None

      redirect_url = body.get("redirectUrl") if isinstance(body, dict) else None
      if not redirect_url:
         raise Exception(
            "@ChineseLegacyAuthStrategy.login: sign In didn't work, could not retrieve auth code. "
            f"status: {status_code}, body: {body}"
         )

      parsed = urlparse(redirect_url)
      query = parse_qs(parsed.query)
      code_values = query.get("code")
      code = code_values[0] if code_values else None

      if not code:
         raise Exception(
            "@ChineseLegacyAuthStrategy.login: AuthCode was not found, you probably need to migrate your account."
         )

      return {
         "code": code,  # type: ignore[return-value]
         "cookies": cookie_jar,
      }