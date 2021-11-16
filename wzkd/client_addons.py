import asyncio
import os
import dotenv


import callofduty
from callofduty import Mode, Title, Language
from callofduty.client import Client



# following additional methods to be added in callofduty.client.py Client Class
# Will be imported into respective class at runtime in app.py
# see notebooks/cod_api_doc.ipnyb for details

async def GetMatches(
    self, platform, username: str, title: Title, mode: Mode, **kwargs
):

    limit: int = kwargs.get("limit", 20)
    startTimestamp: int = kwargs.get("startTimestamp", 0)
    endTimestamp: int = kwargs.get("endTimestamp", 0)

    data: dict = (
        await self.http.GetPlayerMatches(
            platform,
            username,
            title.value,
            mode.value,
            limit,
            startTimestamp,
            endTimestamp,
        )
    )["data"] # API res was filtered out here in callofduty.py client

    return data


async def GetMatchesDetailed(
    self, platform, username: str, title: Title, mode: Mode, **kwargs
):

    limit: int = kwargs.get("limit", 20)
    startTimestamp: int = kwargs.get("startTimestamp", 0)
    endTimestamp: int = kwargs.get("endTimestamp", 0)

    return (
        await self.http.GetPlayerMatchesDetailed(
            platform,
            username,
            title.value,
            mode.value,
            limit,
            startTimestamp,
            endTimestamp,
        )
    )["data"]['matches'] # API res was filtered out here in callofduty.py client


async def GetMatchesSummary(
    self, platform, username: str, title: Title, mode: Mode, **kwargs
):

    limit: int = kwargs.get("limit", 20)
    startTimestamp: int = kwargs.get("startTimestamp", 0)
    endTimestamp: int = kwargs.get("endTimestamp", 0)

    return (
        await self.http.GetPlayerMatchesDetailed(
            platform,
            username,
            title.value,
            mode.value,
            limit,
            startTimestamp,
            endTimestamp,
        )
    )["data"]['summary'] # API res was filtered out here in callofduty.py client


async def GetProfile(
    self, platform, username: str, title: Title, mode: Mode, **kwargs
):
    """ 
    Compared to client : modified so that we do not use Platform.abc as parameter
    but instead our app-defined workflow (drop down menu) to select our platform of choice"
    """
    return (
        await self.http.GetPlayerProfile(
            platform, username, title.value, mode.value
        )
    )["data"]


async def GetMatchStats(
    self, platform, title: Title, mode: Mode, matchId: int, language: Language = Language.English, **kwargs
):
    """ 
    Compared to client : modified so that we do not use Platform.abc as parameter
    but instead our app-defined workflow (drop down menu) to select our platform of choice"
    """
    return (
        await self.http.GetFullMatch(
            title.value, platform, mode.value, matchId, language.value
        )
    )["data"]["allPlayers"]
    # api result, at very least for Warzone {'data':{'all_players:' is the only key},'status': call status}

