import json
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any, Dict, Optional, Protocol, TypedDict
from urllib.parse import urlparse, parse_qs

import requests


class Code(str):
   pass


class AuthStrategy(Protocol):
   @property
   def name(self) -> str:
      ...

   def login(
      self,
      user: Dict[str, str],
      options: Optional[Dict[str, Any]] = None
   ) -> Dict[str, Any]:
      ...


@dataclass(frozen=True)
class AustraliaBrandEnvironment:
   endpoints: Any


class AustraliaAuthStrategy(AuthStrategy):
   def __init__(self, environment: AustraliaBrandEnvironment):
      self.environment = environment

   @property
   def name(self) -> str:
      return "AustraliaAuthStrategy"

   def login(
      self,
      user: Dict[str, str],
      options: Optional[Dict[str, Any]] = None
   ) -> Dict[str, Any]:
      cookie_jar = None
      if options is not None:
         cookie_jar = options.get("cookieJar")
      if cookie_jar is None:
         cookie_jar = CookieJar()

      session = requests.Session()
      session.cookies = cookie_jar

      session.get(self.environment.endpoints.session)

      resp = session.post(
         self.environment.endpoints.login,
         headers={
            "Content-Type": "text/plain",
         },
         data=json.dumps(
            {
               "email": user["username"],
               "password": user["password"],
               "mobileNum": "",
            }
         )
      )

      body_str = resp.text
      status_code = resp.status_code

      try:
         body = json.loads(body_str) if body_str else {}
      except Exception:
         body = {}

      redirect_url = body.get("redirectUrl") if isinstance(body, dict) else None
      if not redirect_url:
         raise Exception(
            "@AustraliaAuthStrategy.login: sign In didn't work, could not retrieve auth code. "
            f"status: {status_code}, body: {json.dumps(body)}"
         )

      parsed = urlparse(redirect_url)
      query = parse_qs(parsed.query)
      code_list = query.get("code")
      code = code_list[0] if code_list else None

      if not code:
         raise Exception(
            "@AustraliaAuthStrategy.login: AuthCode was not found, you probably need to migrate your account."
         )

      return {
         "code": Code(code),
         "cookies": cookie_jar,
      }