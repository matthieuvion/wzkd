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

    return list(set(teammates))


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

    def gulag_format(gulag_value):
        return str(int(gulag_value * 100)) + " %"

    agg_session.gulagStatus = agg_session.gulagStatus.apply(gulag_format)

    return agg_session


def get_session_weapons(last_session):
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

    return weapons_stats
