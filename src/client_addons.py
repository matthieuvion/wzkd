import asyncio
import os
import dotenv
import itertools
import backoff
import httpx

import callofduty
from callofduty import Mode, Title, Language
from callofduty.client import Client

from src.decorators import run_mode


""" 
Inside
------
Define additional methods to be added in callofduty.client.py Client Class
The will then be imported into respective class at runtime when we run app.py
Cf. notebooks/cod_api_doc.ipnyb or matches.ipnyb if you're lost

The addons aim at:
- Change the way data was truncated after being sent back by COD API
- Add some backoff / retry to handle (some of) API availability/rates limitations
- Add a new method that loop over matches to go deeper into Matches history
- Add a new method that loop over several matches ids to get several detailed match stats
- @run_mode decorator allow the streamlit app to run in offline mode, using "fake" api result
"""


@run_mode
@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=45, max_tries=8)
async def GetProfile(self, platform, username: str, title: Title, mode: Mode, **kwargs):
    """
    Get Player's profile stats
    """
    return (
        await self.http.GetPlayerProfile(platform, username, title.value, mode.value)
    )["data"]


@run_mode
@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=45, max_tries=8)
async def GetMatchesDetailed(
    self, platform, username: str, title: Title, mode: Mode, **kwargs
):
    """Returns matches history, with username's stats for every match

    Modifications compared to callofduty.py > client.GetPlayerMatches :
     - removed if platform == 'Activision', no longer supported by API
     - filtered out summary data from API's matches res: ['data'] becomes ['data']['matches']
     - default number of matches returned is now 20 (max allowed by the API) instead of 10
     - added @backoff decorator to handle (some of) API rate/availability limits
    """
    limit: int = kwargs.get("limit", 10)
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
    )["data"][
        "matches"
    ]  # originally (in callofduty.py client), API result was truncated here


@run_mode
async def getMoreMatchesDetailed(client, platform, username, title, mode, **kwargs):
    """Loop GetMatchesDetailed() to go deeper into matches history,

    Use endTimestamp argument in GetMatchesDetailed() as a delimiter
    Built to loop till we collect enough Battle Royale Matches,
    as specified with min_br_matches (20 by default)
    """

    min_br_matches = kwargs.get("min_br_matches", 20)
    count_br_matches = 0
    all_batchs = []
    endTimestamp = 0

    while count_br_matches < min_br_matches:
        batch_20 = await client.GetMatchesDetailed(
            platform, username, title, mode, endTimestamp=endTimestamp
        )
        print("got one batch of 20 matches")
        endTimestamp = batch_20[-1]["utcStartSeconds"] * 1000
        count_br_matches += sum(["br_br" in match["mode"] for match in batch_20])
        print(f"count_br_matches: {count_br_matches}")
        all_batchs.append(batch_20)

    return list(itertools.chain(*all_batchs))


@run_mode
@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=45, max_tries=8)
async def GetMatchStats(
    self,
    platform,
    title: Title,
    mode: Mode,
    matchId: int,
    language: Language = Language.English,
    **kwargs,
):
    """Returns all players detailed stats for one match, given a specified match id"""
    return (
        await self.http.GetFullMatch(
            title.value, platform, mode.value, matchId, language.value
        )
    )["data"]["allPlayers"]
    # api result, at very least for Warzone calls  {'data':{'all_players:' is the only key},'status': call status}


@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=45, max_tries=8)
async def GetMatches(self, platform, username: str, title: Title, mode: Mode, **kwargs):
    """Returns matches history, notably matches Ids"""

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
    )[
        "data"
    ]  # originally (in callofduty.py client), API result was truncated here

    return data


@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=10, max_tries=5)
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
    )["data"][
        "summary"
    ]  # originally (in callofduty.py client), API result was truncated here
