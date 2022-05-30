import asyncio
import os
import dotenv
import itertools

import backoff
import httpx
from httpx import Response

import callofduty
from callofduty import Mode, Title, Language
from callofduty.client import Client
from callofduty.http import HTTP
from callofduty.errors import Forbidden, HTTPException, NotFound
from callofduty.http import JSONorText

from src.decorators import run_mode


""" 
Inside
------

Edit or define additional methods in callofduty.client.py, specifically http and client modules
The "new" methods will then be imported into respective class at runtime when we run app.py
Cf. notebooks/cod_api_doc.ipnyb or matches.ipnyb if you're lost

The addons aim at:
1. Tweak in Class HTTP:
- add a default httpx.Timeout of 15 sec (original code : wasn't specified = 5 by default)

2. Additional/replacing methods in Class Client :
- Change the way data was truncated by codclient.py, after being sent back by COD API
- Add some backoff / retry to handle (some of) API availability/rates limitations
- Add a new method that loop over matches to go deeper into Matches history
- Add a new method that loop over several matches ids to get several detailed match stats
- @run_mode decorator allow the streamlit app to run in offline mode, using "fake" api results
"""


""" 1. http module, class HTTP, method Send """


async def Send(self, req):
    """
    Perform an HTTP request
    """

    # // to original client :  add a httpx.Timeout argument
    timeout = httpx.Timeout(15.0, connect=20.0)

    req.SetHeader("Authorization", f"Bearer {self.auth.AccessToken}")
    req.SetHeader("x_cod_device_id", self.auth.DeviceId)

    # // to original client : Timeout argument passed every time we call the COD API
    async with self.session as client:
        res: Response = await client.request(
            req.method, req.url, headers=req.headers, json=req.json, timeout=timeout
        )

        data = await JSONorText(res)
        if isinstance(data, dict):
            status = data.get("status")

            # The API tends to return HTTP 200 even when an error occurs
            if status == "error":
                raise HTTPException(res.status_code, data)

        # HTTP 2XX: Success
        if 300 > res.status_code >= 200:
            return data

        # HTTP 429: Too Many Requests
        if res.status_code == 429:
            # TODO Handle rate limiting
            raise HTTPException(res.status_code, data)

        # HTTP 500/502: Internal Server Error/Bad Gateway
        if res.status_code == 500 or res.status_code == 502:
            # TODO Handle Unconditional retries
            raise HTTPException(res.status_code, data)

        # HTTP 403: Forbidden
        if res.status_code == 403:
            raise Forbidden(res.status_code, data)
        # HTTP 404: Not Found
        elif res.status_code == 404:
            raise NotFound(res.status_code, data)
        else:
            raise HTTPException(res.status_code, data)


""" 2. client module, class Client, several methods """


@run_mode
@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=25, max_tries=5)
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
    as specified with min_br_matches (10 by default)
    Either API limits or just inconsistancy/service down, does not handle well more than 2-3 calls in a row
    """

    min_br_matches = kwargs.get("min_br_matches", 10)
    count_br_matches = 0
    all_batchs = []
    endTimestamp = 0

    while count_br_matches < min_br_matches:
        batch_20 = await client.GetMatchesDetailed(
            platform, username, title, mode, endTimestamp=endTimestamp
        )
        endTimestamp = batch_20[-1]["utcStartSeconds"] * 1000
        count_br_matches += sum(["br_br" in match["mode"] for match in batch_20])
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
    # api result, at very least for Warzone calls return as :
    # {'data':{'all_players:' is the only key},'status': call status}


@backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=45, max_tries=8)
async def GetMatches(self, platform, username: str, title: Title, mode: Mode, **kwargs):
    """Returns matches history, notably matches Ids -without stats"""

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
