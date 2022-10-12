import pandas as pd


""" 
Inside
------
Aggregate detailed stats for a session of matches, here our last matches (BR / Resurgence) played.

- Before that we collected a list of matches ids, username, and collected detailed stats for thoses ids.
- Also our API output (detailed matches stats) was already converted to a df,
  flattened and formated to be readable / operable (using api_format module)
"""


def get_teammates(last_session_formatted, gamertag):
    """Get list of teammates from your last session of BR matches"""
    ids = last_session_formatted.query("username == @gamertag")["matchID"].tolist()
    teams = last_session_formatted.query("username == @gamertag")["team"].tolist()
    teammates = []
    for id_, team in zip(ids, teams):
        teammates.extend(
            last_session_formatted.query("matchID == @id_ & team == @team")[
                "username"
            ].tolist()
        )

    return sorted(list(set(teammates)), key=str.lower)


def team_aggregated_stats(last_session_formatted, teammates):
    """last session > n battle royale / Resurgence matches > formatted => team agregated stats"""

    aggregations = {
        "mode": "count",
        "kills": "sum",
        "deaths": "sum",
        "assists": "sum",
        "damageDone": "mean",
        "damageTaken": "mean",
        "gulagStatus": lambda x: (x.eq("W").sum() / x.isin(["W", "L"]).sum())
        if x.eq("W").sum() > 0  # -_-
        else 0,
    }

    team_session = (
        last_session_formatted.query("username in @teammates")
        .groupby("username")
        .agg(aggregations)
        .rename(columns={"mode": "played"})
        .reset_index()
    )
    team_session["kdRatio"] = team_session.kills / team_session.deaths
    team_session.sort_values(
        by="username", key=lambda col: col.str.lower(), inplace=True
    )

    def extract_best_loadout(last_session_formatted, teammates):
        """Extract loadout (1) of the game with the highest kd"""
        # prior, both last_session and teammates are sorted alphabetically by username
        loadout_idx = [
            last_session_formatted.query("@user in username")["kdRatio"].idxmax()
            for user in teammates
        ]
        return [
            last_session_formatted.iloc[loadout_i]["loadout_1"]
            for loadout_i in loadout_idx
        ]

    def gulag_format(gulag_value):
        return str(int(gulag_value * 100)) + " %"

    def remove_session_teammates(team_session):
        """Remove some of random people you played with"""
        return team_session.sort_values(by="played", ascending=False).head(4)

    best_loadout = extract_best_loadout(last_session_formatted, teammates)
    team_session.insert(2, "loadoutBest", best_loadout)
    team_session.gulagStatus = team_session.gulagStatus.apply(gulag_format)
    team_session = remove_session_teammates(team_session)

    return team_session


def get_players_weapons(last_session_formatted):
    """Compute overall session weapons stats for Loadout 1, all players, all session' matches"""

    df_weapons = last_session_formatted[["kills", "deaths", "loadout_1"]]
    df_weapons[["w1", "w2"]] = last_session_formatted["loadout_1"].str.split(
        " ", expand=True
    )

    first_agg = {"loadout_1": "count", "kills": "sum", "deaths": "sum"}
    primary = (
        df_weapons.groupby("w1")
        .agg(first_agg)
        .reset_index()
        .rename(columns={"w1": "weapon", "loadout_1": "count"})
    )
    secondary = (
        df_weapons.groupby("w2")
        .agg(first_agg)
        .reset_index()
        .rename(columns={"w2": "weapon", "loadout_1": "count"})
    )
    weapons_long = pd.concat([primary, secondary])

    second_agg = {"count": "sum", "kills": "sum", "deaths": "sum"}

    weapons_stats = weapons_long.groupby("weapon").agg(second_agg)
    weapons_stats["kdRatio"] = weapons_stats["kills"] / weapons_stats["deaths"]
    weapons_stats["pickRate"] = (
        weapons_stats["count"] * 100 / (weapons_stats["count"].sum() / 2)
    )

    def filter_players_weapons(weapons):
        """Remove non consistent data from Weapons df (underplayed etc..)"""
        weapons = weapons.sort_values(by="pickRate", ascending=False)[:10]
        return weapons

    weapons_stats = filter_players_weapons(weapons_stats)

    return weapons_stats.reset_index()


def player_stats(last_session_formatted, gamertag):
    """
    Extract app's user (gamertag) stats only, from last session matches (with teammates/opponent data)
    """

    visible_cols = [
        "utcEndSeconds",
        "mode",
        "teamPlacement",
        "kills",
        "deaths",
        "assists",
    ]
    player_df = last_session_formatted.query("username == @gamertag")

    return player_df[visible_cols]
