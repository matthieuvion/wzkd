import itertools
import asyncio
from typing import AsyncContextManager

import streamlit as st
from async_lru import alru_cache
import backoff
import httpx

from wzlight import Api

"""
Inside
-----
wzlight client enhancements

- New class EnhancedApi than inherit wzlight Api Clsvariables and methods
- Add async-compatible caching with async_lru lib to avoid consuming too many calls
- Add backoff with backoff lib
- Basic rate/concurrency limits e.g. getting data of list[matches]) w/ asyncio.Semaphore
- New method to loop over GetRecentMatches (history)
- New method to requests detailed several match stats (GetMatch) concurrently

"""


class EnhancedApi(Api):
    """Inherits wzlight Api Cls, add or enhance default methods"""

    def __init__(self, sso):
        super().__init__(sso)

    @alru_cache(maxsize=8)
    @backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=10, max_tries=2)
    async def GetProfileCached(self, httpxClient, platform, username):
        """Tweak Api.GetProfile adding caching, backoff"""

        return await self.GetProfile(httpxClient, platform, username)

    @alru_cache(maxsize=128)
    @backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=25, max_tries=5)
    async def GetMatchSafe(
        self,
        httpxClient,
        platform,
        matchId: int,
        sema: AsyncContextManager,
    ):
        """Tweak Api.GetMatch adding caching, backoff, async.Semaphore limit object"""

        async with sema:
            r = await self.GetMatch(httpxClient, platform, matchId)
            await asyncio.sleep(1)
            if sema.locked():
                print("Concurrency limit reached, waiting ...")
                await asyncio.sleep(2)
            return r

    async def GetMatchList(self, httpxClient, platform, matchIds: list[int]):
        """New Api method : run GetMatchSafe (--> Api.GetMatch) async/"concurrently",
        with a limit,  given a list of MatchIds.
        """

        sema = asyncio.Semaphore(2)
        tasks = []
        for matchId in matchIds:
            tasks.append(self.GetMatchSafe(httpxClient, platform, matchId, sema))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return list(itertools.chain(*results))

    @alru_cache(maxsize=128)
    @backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=20, max_tries=3)
    async def GetRecentMatchesWithDateCached(
        self, httpxClient, platform, username, endTimestamp
    ):
        """Tweak Api.GetRecentMatchesWithDate adding caching, backoff"""

        return await self.GetRecentMatchesWithDate(
            httpxClient, platform, username, endTimestamp
        )

    @backoff.on_exception(backoff.expo, httpx.HTTPError, max_time=20, max_tries=3)
    async def GetRecentMatchesNotCached(self, httpxClient, platform, username):
        """Tweak Api.GetRecentMatches adding backoff (and no cache!)"""
        await asyncio.sleep(0.5)
        return await self.GetRecentMatches(httpxClient, platform, username)

    async def GetRecentMatchesWithDateLoop(
        self, httpxClient, platform, username, **kwargs
    ):
        """New Api method :
        After a first --not cached, call to Recent Matches (history),
        loop over GetRecentMatchesWithDateCached, so we get n * 20 recent matches
        """

        max_calls = kwargs.get("max_calls", 5)
        ncalls = 0

        all_batchs = []

        # A mandatory --not cached, 1st call because we want an updated history""
        updated_history = await self.GetRecentMatchesNotCached(
            httpxClient, platform, username
        )
        endTimestamp = updated_history[-1]["utcStartSeconds"] * 1000
        all_batchs.append(updated_history)
        ncalls += 1

        while ncalls < max_calls:
            # if EndtimeStamp does not change @call, will return a cached value
            batch_20 = await self.GetRecentMatchesWithDateCached(
                httpxClient, platform, username, endTimestamp
            )
            endTimestamp = batch_20[-1]["utcStartSeconds"] * 1000
            all_batchs.append(batch_20)
            ncalls += 1
            await asyncio.sleep(0.5)

        return list(itertools.chain(*all_batchs))
