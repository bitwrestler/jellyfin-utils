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
        import os
        import sys

        if os.environ.get("REQUESTS_LOGGING", "").lower() in ("true", "1", "yes"):
            import http.client
            import logging

            # 1. Force http.client's internal print statements to go to stderr instead of stdout
            http.client.HTTPConnection.debuglevel = 1
            http.client.print = lambda *args, **kwargs: print(*args, file=sys.stderr, **kwargs)

            # 2. Force reset the root logger to apply your configurations
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.DEBUG)

            # Clear out any pre-existing handlers that are blocking configuration
            if root_logger.hasHandlers():
                root_logger.handlers.clear()

            # 3. Explicitly attach a StreamHandler pointing to stderr
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            root_logger.addHandler(handler)

            # 4. Set underlying library levels
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
