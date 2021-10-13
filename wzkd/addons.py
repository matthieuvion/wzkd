import asyncio
import os
import dotenv


import callofduty
from callofduty import Mode, Platform, Title
from callofduty.client import Client



# following additional methods to be added in callofduty.client.py Client Class
# see notebooks/cod_api_doc.ipnyb for details

async def GetMatches(
    self, platform: Platform, username: str, title: Title, mode: Mode, **kwargs
):

    limit: int = kwargs.get("limit", 20)
    startTimestamp: int = kwargs.get("startTimestamp", 0)
    endTimestamp: int = kwargs.get("endTimestamp", 0)

    data: dict = (
        await self.http.GetPlayerMatches(
            platform.value,
            username,
            title.value,
            mode.value,
            limit,
            startTimestamp,
            endTimestamp,
        )
    )["data"] # API res was filtered out here

    return data


async def GetMatchesDetailed(
    self, platform: Platform, username: str, title: Title, mode: Mode, **kwargs
):

    limit: int = kwargs.get("limit", 20)
    startTimestamp: int = kwargs.get("startTimestamp", 0)
    endTimestamp: int = kwargs.get("endTimestamp", 0)

    return (
        await self.http.GetPlayerMatchesDetailed(
            platform.value,
            username,
            title.value,
            mode.value,
            limit,
            startTimestamp,
            endTimestamp,
        )
    )["data"]['matches'] # API res was filtered out here


async def GetMatchesSummary(
    self, platform: Platform, username: str, title: Title, mode: Mode, **kwargs
):

    limit: int = kwargs.get("limit", 20)
    startTimestamp: int = kwargs.get("startTimestamp", 0)
    endTimestamp: int = kwargs.get("endTimestamp", 0)

    return (
        await self.http.GetPlayerMatchesDetailed(
            platform.value,
            username,
            title.value,
            mode.value,
            limit,
            startTimestamp,
            endTimestamp,
        )
    )["data"]['summary'] # API res was filtered out here


# add our modified methods into callofduty Client Class

Client.GetMatches = GetMatches
Client.GetMatchesDetailed = GetMatchesDetailed
Client.GetMatchesSummary = GetMatchesSummary


# async def GetMatchesHistory(
#     self, platform: Platform, username: str, title: Title, mode: Mode, **kwargs
# ):
#     
# 
#     return
# 



