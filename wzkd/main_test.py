import asyncio

import callofduty
from callofduty import Mode, Platform, Title

# ACT_SSO_COOKIE
sso = "MjYyMTg1OTc3OTU4MDY1MDY5NjoxNjMzMzYzNTA2NjkyOjVhNGI2YTI0MGVkNjNhNzAzMjA2MmU1NTZiOWQxNzAw"
player_name = "confetti_seeker"

async def main():
    client = await callofduty.Login(sso=sso)
    
    results = await client.SearchPlayers(Platform.PlayStation, player_name, limit=20)
    
    print(f"Searching player: {player_name}, number of results: {len(results)}")
    if results is not None:
        if len(results) > 1:
            for player in results:
                print(f"{player.username} ({player.platform.name})")

        player = results[0]
        profile = await player.profile(Title.ModernWarfare, Mode.Warzone)
        
        print(profile.keys())
        
        level = profile["level"]
        kd = profile["lifetime"]["all"]["properties"]["kdRatio"]

        print(f"\n{player.username} ({player.platform.name})")
        print(f"Lifetime results | Level: {level}, K/D Ratio: {kd}")

asyncio.get_event_loop().run_until_complete(main())