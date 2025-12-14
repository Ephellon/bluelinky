import requests
from http.cookiejar import CookieJar
from typing import Any, Dict, Optional

from ...constants.europe import EULanguages, EuropeanBrandEnvironment
from .auth_strategy import AuthStrategy, Code, initSession
from urllib.parse import urlparse, parse_qs


class EuropeanLegacyAuthStrategy(AuthStrategy):
   def __init__(self, environment: EuropeanBrandEnvironment, language: EULanguages):
      self.environment = environment
      self.language = language

   @property
   def name(self) -> str:
      return "EuropeanLegacyAuthStrategy"

   def login(
      self,
      user: Dict[str, str],
      options: Optional[Dict[str, Any]] = None
   ) -> Dict[str, Any]:
      cookie_jar_in: Optional[CookieJar] = None
      if options is not None:
         cookie_jar_in = options.get("cookieJar")

      cookieJar = initSession(self.environment, cookie_jar_in)

      response = requests.post(
         self.environment.endpoints.login,
         json={
            "email": user["username"],
            "password": user["password"],
         },
         cookies=cookieJar,
      )

      statusCode = response.status_code
      try:
         body = response.json()
      except Exception:
         body = {}

      redirect_url = None
      if isinstance(body, dict):
         redirect_url = body.get("redirectUrl")

      if not redirect_url:
         raise Exception(
            "@EuropeanLegacyAuthStrategy.login: sign In didn't work, could not retrieve auth code. "
            f"status: {statusCode}, body: {body}"
         )

      parsed = urlparse(redirect_url)
      query = parse_qs(parsed.query)
      code_list = query.get("code")
      code = code_list[0] if code_list else None

      if not code:
         raise Exception(
            "@EuropeanLegacyAuthStrategy.login: AuthCode was not found, you probably need to migrate your account."
         )

      return {
         "code": code,  # Code
         "cookies": cookieJar,
      }