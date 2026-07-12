import os
from collections.abc import Iterator
from . import JellyfinConfig


def _get(name: str) -> str | None:
    return os.environ.get(name)

class JellfinConfigFactory:
    JELLYFIN_SERVER_ENV = "JELLYFIN_SERVER"
    JELLYFIN_ACCESS_TOKEN_ENV = "JELLYFIN_ACCESS_TOKEN"
    JELLYFIN_USERNAME_ENV = "JELLYFIN_USERNAME"

    @staticmethod
    def FromEnvironment() -> JellyfinConfig:
        args = (_get(JellfinConfigFactory.JELLYFIN_ACCESS_TOKEN_ENV), _get(JellfinConfigFactory.JELLYFIN_SERVER_ENV), _get(JellfinConfigFactory.JELLYFIN_USERNAME_ENV))
        JellfinConfigFactory._raise_if_missing(args)
        return JellyfinConfig(*args)

    @staticmethod
    def FromEnvironmentList() -> Iterator[JellyfinConfig]:
        server = _get(JellfinConfigFactory.JELLYFIN_SERVER_ENV)
        access_token = _get(JellfinConfigFactory.JELLYFIN_ACCESS_TOKEN_ENV)
        usernames_raw = _get(JellfinConfigFactory.JELLYFIN_USERNAME_ENV)
        JellfinConfigFactory._raise_if_missing((access_token, server, usernames_raw))
        for username in (u.strip() for u in usernames_raw.split(",") if u.strip()):
            yield JellyfinConfig(str(access_token), str(server), username)

    @staticmethod
    def _raise_if_missing(values : tuple[str | None, ...]) -> None:
        if not all(values):
            raise ValueError(f"Missing required Jellyfin environment variables: {JellfinConfigFactory.JELLYFIN_SERVER_ENV}, {JellfinConfigFactory.JELLYFIN_ACCESS_TOKEN_ENV}, {JellfinConfigFactory.JELLYFIN_USERNAME_ENV}")

