import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from ...constants.europe import EULanguages, EuropeanBrandEnvironment
from .auth_strategy import AuthStrategy, Code, initSession

stdHeaders: Dict[str, str] = {
   'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_1 like Mac OS X) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0 Mobile/15B92 Safari/604.1',
}


@dataclass
class _ResponseWrapper:
   url: str
   statusCode: int
   body: str
   headers: Dict[str, Any]


def _extract_cookie_header(cookiejar: Any) -> Optional[str]:
   if cookiejar is None:
      return None
   # Support requests.cookies.RequestsCookieJar (preferred)
   if hasattr(cookiejar, 'get_dict'):
      d = cookiejar.get_dict()
      if not d:
         return None
      return '; '.join([f'{k}={v}' for k, v in d.items()])

   # Best-effort support for other cookie jar types
   try:
      items = []
      for c in cookiejar:
         name = getattr(c, 'name', None)
         value = getattr(c, 'value', None)
         if name is not None and value is not None:
            items.append(f'{name}={value}')
      return '; '.join(items) if items else None
   except Exception:
      return None


def _merge_response_cookies_into_cookiejar(resp: requests.Response, cookiejar: Any) -> None:
   if cookiejar is None:
      return
   # requests cookie jar
   if hasattr(cookiejar, 'update'):
      try:
         cookiejar.update(resp.cookies)
         return
      except Exception:
         pass
   # tough-cookie style jar (best-effort)
   if hasattr(cookiejar, 'set_cookie'):
      try:
         for c in resp.cookies:
            cookiejar.set_cookie(c)
      except Exception:
         return


def _request(
   method: str,
   url: str,
   *,
   cookiejar: Any,
   headers: Dict[str, str],
   data: Optional[str] = None,
   followRedirect: bool = True,
) -> _ResponseWrapper:
   session = requests.Session()
   # Prefer native requests cookie jar behavior when possible
   if cookiejar is not None and hasattr(cookiejar, 'get_dict') and hasattr(cookiejar, 'update'):
      try:
         session.cookies = cookiejar  # type: ignore[assignment]
      except Exception:
         pass

   req_headers = dict(headers or {})
   cookie_header = _extract_cookie_header(cookiejar)
   if cookie_header and 'Cookie' not in req_headers:
      req_headers['Cookie'] = cookie_header

   resp = session.request(
      method=method,
      url=url,
      headers=req_headers,
      data=data,
      allow_redirects=followRedirect,
   )

   _merge_response_cookies_into_cookiejar(resp, cookiejar)

   final_url = str(resp.url)
   status_code = int(resp.status_code)
   body = resp.text if resp.text is not None else ''
   resp_headers = dict(resp.headers)

   return _ResponseWrapper(
      url=final_url,
      statusCode=status_code,
      body=body,
      headers=resp_headers,
   )


class EuropeanBrandAuthStrategy(AuthStrategy):
   def __init__(self, environment: EuropeanBrandEnvironment, language: EULanguages):
      self.environment = environment
      self.language = language

   @property
   def name(self) -> str:
      return 'EuropeanBrandAuthStrategy'

   def login(
      self,
      user: Dict[str, str],
      options: Optional[Dict[str, Any]] = None
   ) -> Dict[str, Any]:
      cookieJar = initSession(self.environment, options.get('cookieJar') if options else None)

      authHost = 'idpconnect-eu.kia.com' if getattr(self.environment, 'brand', None) == 'kia' else 'idpconnect-eu.hyundai.com'

      authUrl = (
         f"https://{authHost}/auth/api/v2/user/oauth2/authorize"
         f"?response_type=code"
         f"&client_id={self.environment.clientId}"
         f"&redirect_uri={self.environment.baseUrl}/api/v1/user/oauth2/redirect"
         f"&lang={self.language}"
         f"&state=ccsp"
      )

      authResponse = _request(
         'GET',
         authUrl,
         cookiejar=cookieJar,
         headers=stdHeaders,
         followRedirect=True,
      )

      urlToCheck = authResponse.url

      connectorSessionKey: Optional[str] = None

      match = re.search(r'connector_session_key%3D([0-9a-fA-F-]{36})', urlToCheck)
      if match:
         connectorSessionKey = match.group(1)

      if not connectorSessionKey:
         match = re.search(r'connector_session_key=([0-9a-fA-F-]{36})', urlToCheck)
         if match:
            connectorSessionKey = match.group(1)

      if not connectorSessionKey:
         raise Exception(f'@EuropeanBrandAuthStrategy.login: Could not extract connector_session_key from URL: {urlToCheck}')

      signinUrl = f'https://{authHost}/auth/account/signin'

      form = {
         'client_id': self.environment.clientId,
         'encryptedPassword': 'false',
         'orgHmgSid': '',
         'password': user['password'],
         'redirect_uri': f'{self.environment.baseUrl}/api/v1/user/oauth2/redirect',
         'state': 'ccsp',
         'username': user['username'],
         'remember_me': 'false',
         'connector_session_key': connectorSessionKey,
         '_csrf': '',
      }
      formData = '&'.join([f'{requests.utils.quote(str(k))}={requests.utils.quote(str(v))}' for k, v in form.items()])

      signinResponse = _request(
         'POST',
         signinUrl,
         cookiejar=cookieJar,
         data=formData,
         headers={
            'content-type': 'application/x-www-form-urlencoded',
            'origin': f'https://{authHost}',
            **stdHeaders,
         },
         followRedirect=False,
      )

      if signinResponse.statusCode != 302:
         raise Exception(f'@EuropeanBrandAuthStrategy.login: Signin failed with status {signinResponse.statusCode}: {signinResponse.body}')

      location = None
      for key in ('location', 'Location'):
         if key in signinResponse.headers:
            location = signinResponse.headers.get(key)
            break

      if not location:
         raise Exception('@EuropeanBrandAuthStrategy.login: No redirect location found after signin')

      codeMatch = re.search(r'code=([0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36})', location)
      if not codeMatch:
         altMatch = re.search(r'code=([^&]+)', location)
         if altMatch:
            code = altMatch.group(1)
            return {'code': code, 'cookies': cookieJar}
         raise Exception(f'@EuropeanBrandAuthStrategy.login: Could not extract authorization code from redirect location: {location}')

      code = codeMatch.group(1)

      return {
         'code': code,
         'cookies': cookieJar,
      }