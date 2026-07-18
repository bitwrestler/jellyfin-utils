import os
import requests
from typing import Callable

from . import JellyfinConfig


class IJellyfinRequestAdapter:
    def MakeGetRequest(self, endpoint: str, params: dict | None = None) -> dict | None:
        pass
    def MakePostRequest(self, endpoint : str, content : dict)-> dict | None:
        pass
    def MakeDeleteRequest(self, endpoint: str, params: dict | None = None) -> dict | None:
        pass

class JellyfinRequestAdapter(IJellyfinRequestAdapter):
    APPLICATION_JSON="application/json"
    CONTENT_TYPE_HEADER="Content-Type"
    X_EMBY_TOKEN="X-Emby-Token"
    ACCEPT="Accept"


    def __init__(self, config : JellyfinConfig) -> None:
        self.config = config
        if os.environ.get("REQUESTS_LOGGING", "").lower() in ("true", "1", "yes"):
            import http.client
            import logging
            import requests
            # 1. Force low-level http client debugging to show wire traffic
            http.client.HTTPConnection.debuglevel = 1
            # 2. Setup standard logging output format
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            # 3. Force urllib3 to output all its underlying debug statements
            logging.getLogger("urllib3").setLevel(logging.DEBUG)

    def _request(self, endpoint : str, request_callback : Callable[ [str,dict[str,str] ], requests.Response]) -> dict | None:
        url = f"{self.config.ServerURL}/{endpoint}"
        headers = {
            JellyfinRequestAdapter.X_EMBY_TOKEN: self.config.AccessToken,
            JellyfinRequestAdapter.ACCEPT: JellyfinRequestAdapter.APPLICATION_JSON
        }
        try:
            response = request_callback(url, headers)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError):
            return None

    def MakeGetRequest(self, endpoint : str, params : dict | None = None) -> dict | None:
        def request_callback(url : str, headers : dict[str,str]) -> requests.Response:
            return requests.get(url, headers=headers, params=params)
        return self._request(endpoint, request_callback)

    def MakeDeleteRequest(self, endpoint : str, params : dict | None = None) -> dict | None:
        def request_callback(url : str, headers : dict[str,str]) -> requests.Response:
            return requests.delete(url, headers=headers, params=params)
        return self._request(endpoint, request_callback)

    def MakePostRequest(self, endpoint : str, content : dict) -> dict | None:
        def request_callback(url : str, headers : dict[str,str]) -> requests.Response:
            headers.update({JellyfinRequestAdapter.CONTENT_TYPE_HEADER: JellyfinRequestAdapter.APPLICATION_JSON})
            return requests.post(url, headers=headers, json=content)
        return self._request(endpoint, request_callback)
