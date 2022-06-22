import itertools
import pandas as pd


""" 
Inside
------
Aggregate detailed stats for a session of matches, here our last matches played.

- Before that we collected a list of matches ids, username, and collected detailed stats for thoses ids.
- Also our API output (detailed matches stats) was already converted to a df, flattened and formated to be readable / operable (using api_format module)
"""


def get_session_teammates(last_session, gamertag):
    """Get list of teammates from your last session of BR matches"""
    ids = last_session.query("username == @gamertag")["matchID"].tolist()
    teams = last_session.query("username == @gamertag")["team"].tolist()
    teammates = []
    for id_, team in zip(ids, teams):
        teammates.extend(
            last_session.query("matchID == @id_ & team == @team")["username"].tolist()
        )

    return sorted(list(set(teammates)), key=str.lower)


def stats_last_session(last_session, teammates):
    """last session > n battle royale matches > formatted => agregated stats"""

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

    agg_session = (
        last_session.query("username in @teammates")
        .groupby("username")
        .agg(aggregations)
        .rename(columns={"mode": "played"})
        .reset_index()
    )
    agg_session["kdRatio"] = agg_session.kills / agg_session.deaths
    agg_session.sort_values(
        by="username", key=lambda col: col.str.lower(), inplace=True
    )

    def extract_best_loadout(last_session, teammates):
        # prior, both last_session and teammates are sorted alphabetically by username
        loadout_idx = [
            last_session.query("@user in username")["kdRatio"].idxmax()
            for user in teammates
        ]
        return [last_session.iloc[loadout_i]["loadout_1"] for loadout_i in loadout_idx]

    def gulag_format(gulag_value):
        return str(int(gulag_value * 100)) + " %"

    best_loadout = extract_best_loadout(last_session, teammates)
    agg_session.insert(2, "loadoutBest", best_loadout)
    agg_session.gulagStatus = agg_session.gulagStatus.apply(gulag_format)

    return agg_session


def get_players_weapons(last_session):
    """Compute overall session weapons stats for Loadout 1"""

    df_weapons = last_session[["kills", "deaths", "loadout_1"]]
    df_weapons[["w1", "w2"]] = last_session["loadout_1"].str.split(" ", expand=True)

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
