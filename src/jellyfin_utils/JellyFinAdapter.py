import re
from dataclasses import dataclass
from typing import Generator

from . import JellyfinConfig
from .JellyfinRequestAdapter import IJellyfinRequestAdapter, JellyfinRequestAdapter

def get_episode_title(filepath):
    def get_episode_title_fallback(file_path):
        basename = file_path.rsplit('/', 1)[-1]  # remove directory path from filepath
        stem = basename[:-3]

        parts = stem.split(' - ')
        if len(parts) > 1:
            return parts[-2]
        else:
            return ""
    def get_episode_title_primary(file_path):
        basename = file_path.rsplit('/', 1)[-1]  # remove directory path from filepath
        stem = basename[:-3]

        pattern = r'\s\d+[\w\-_]*\s*-\s*'
        match = re.search(pattern, stem)

        if match:
            return stem.split(match.group()).pop()
        else:
            parts = stem.split('\n')  # fallback to split on newline if the pattern is not found
            if len(parts) > 1:
                return parts[-1]
            else:
                return ""
    return get_episode_title_primary(filepath) or get_episode_title_fallback(filepath)


@dataclass
class JellyfinItem:
    Id : str
    Played : bool
    Favorite : bool
    MatchesPath : bool

class IJellyFinAdapter:
    def Requesthandler(self) -> IJellyfinRequestAdapter:
        pass
    def GetUserId(self) -> str | None:
        pass
    def GetItemUserInformation(self,id : str) -> dict|None:
        pass
    def DeleteItem(self, id : str) -> dict|None:
        pass
    def QueryRecordingItem(self, filePath : str, titleSearch : bool = True) -> list[JellyfinItem]:
        pass
    def MarkPlayedFlag(self, items : list[JellyfinItem]) -> None:
        pass


class JellyFinAdapter(IJellyFinAdapter):
    def __init__(self, config : JellyfinConfig, request_handler : IJellyfinRequestAdapter|None = None):
        if not config:
            raise Exception("No Jellyfin config provided")
        self.cached_user_id = None
        self.config = config
        self.request_handler = request_handler or JellyfinRequestAdapter(config)

    @property
    def Requesthandler(self) -> IJellyfinRequestAdapter:
        return self.request_handler

    def GetUserId(self) -> str | None:
        if self.cached_user_id:
            return self.cached_user_id
        json = self.request_handler.MakeGetRequest("Users")
        if not json:
            return None
        users = [user for user in json if user.get("Name") == self.config.UserName]
        if users:
            self.cached_user_id = users[0].get("Id")
            return self.cached_user_id
        return None

    def GetItemUserInformation(self,id : str) -> dict|None:
        userid = self.GetUserId()
        if not userid:
            return None
        params = {"userId": userid}
        return self.request_handler.MakeGetRequest(f"UserItems/{id}/UserData", params)

    def DeleteItem(self, id : str) -> dict|None:
        p = { "itemId": id }
        return self.request_handler.MakeDeleteRequest(f"Items", p)

    USER_DATA_PLAYED_PROPERTY_NAME = "Played"
    USER_DATA_FAVORITE_PROPERTY_NAME = "IsFavorite"
    @staticmethod
    def _get_played_value(values : dict) -> bool:
        return values[JellyFinAdapter.USER_DATA_PLAYED_PROPERTY_NAME]
    @staticmethod
    def _set_played_value(vals : dict, played : bool) -> None:
        vals[JellyFinAdapter.USER_DATA_PLAYED_PROPERTY_NAME] = played
    @staticmethod
    def _get_favorite_value(values : dict) -> bool:
        return values[JellyFinAdapter.USER_DATA_FAVORITE_PROPERTY_NAME]

    def _findItemsInResult(self,filePath : str, jsonResult : dict) -> Generator[JellyfinItem, None, None]:
        coll = jsonResult["Items"]
        if len(coll)==0:
            return
        collObj = [item for item in jsonResult["Items"]]
        for ele in collObj:
            myid = ele["Id"]
            udObj = self.GetItemUserInformation(myid)
            if not udObj:
                continue
            matches = ele["Path"] == filePath
            isPlayed = JellyFinAdapter._get_played_value(udObj)
            isFavorite = JellyFinAdapter._get_favorite_value(udObj)
            yield JellyfinItem(myid, isPlayed,isFavorite, matches)
    def QueryRecordingItem(self, filePath : str, titleSearch : bool = True) -> list[JellyfinItem]:
        query = {
            "recursive": "true",
            "fields": "path",
            "includedItemsTypes": "Recording",
            "mediaTypes": "Video"
        }
        if filePath and titleSearch:
            episodeTitle = get_episode_title(filePath)
            if episodeTitle:
                query.update({"searchTerm" : episodeTitle})
        json = self.request_handler.MakeGetRequest("Items", query)
        if not json and titleSearch:
            return self.QueryRecordingItem(filePath,False)
        if not json:
            return []
        return list(self._findItemsInResult(filePath, json))

    def _mark_implementation(self, itemid : str) -> dict|None:
        userid = self.GetUserId()
        if not userid:
            return
        currentData = self.GetItemUserInformation(itemid)
        if not currentData or not JellyFinAdapter._get_played_value(currentData):
            return
        JellyFinAdapter._set_played_value(currentData, True)
        return self.request_handler.MakePostRequest(f"UserItems/{itemid}/UserData?userid={userid}", currentData)


    def MarkPlayedFlag(self, items : list[JellyfinItem]) -> None:
        if len(items) < 2:
            return
        played_ids = [item.Id for item in items if item.Played]
        unplayed_ids = [item.Id for item in items if not item.Played and item.MatchesPath]
        # If no items were ever marked as played or nothing to fix, bail out.
        if not played_ids:
            return
        if not unplayed_ids:
            return
        for unmarked in unplayed_ids:
            self._mark_implementation(unmarked)