import datetime
from datetime import datetime, timezone
from doctest import DocFileTest
import pandas as pd
import numpy as np
import toml
import json

# CONF utils


def load_labels(file="src/wz_labels.json"):
    """--> dict, with data needed to parse weapons, games modes etc."""
    with open(file) as f:
        LABELS = json.load(f)
    return LABELS


def load_conf(file="src/conf.toml"):
    """--> dict, overall app config : run in offline mode, display Battle Royale games only etc."""
    with open(file) as f:
        CONF = toml.load(f)
    return CONF


# Retrieve ids, names, dates...


def get_last_match_id(matches):
    """Extract last (Battle Royale) Match ID from list of last matches"""
    list_br_match = [match for match in matches if "br_br" in match["mode"]]
    last_match_id = int(list_br_match[0]["matchID"]) if len(list_br_match) > 0 else None
    return last_match_id


def get_last_br_ids(history, LABELS):
    """Extract battle royale matches IDs from latest session with br matches"""
    br_modes = [value for value in LABELS.get("modes").get("battle_royale").values()]
    session_idx_min = history.query("mode in @br_modes").session.min()

    br_ids = (
        history.query("mode in @br_modes")
        .groupby("session")
        .get_group(session_idx_min)
        .matchID.tolist()
    )
    return [int(br_id) for br_id in br_ids]


def get_gamertag(matches):
    """
    A player can be searchable with a given name but having a different gamertag in-game
    Because you can change your gamertag and choose something different than your "main profile"
    If you want to analyse data from player's / his team perspective, gamertag can be retrieve
    through results sent back by GetMatchesDetailed(), in 'username' column
    """
    return matches["username"][0]


def get_team(df, gamertag):
    """--> str, Retrieve team name of given gamertag"""
    return df[df["username"] == gamertag]["team"].tolist()[0]


def get_teammates(df, gamertag):
    """--> list(str), Retrieve list of gamertag + his teammates"""
    team = get_team(df, gamertag)
    return df[df["team"] == team]["username"].tolist()


def get_date(df):
    """--> str, Retrieve end date (str) of our match"""
    return df["utcEndSeconds"][0].strftime("%Y-%m-%d %H:%M")


def get_mode(df):
    """--> str, retrieve BR type of our match"""
    return df["mode"][0]


# formatting tools


def concat_cols(df, to_concat, sep):
    check = to_concat[0]
    if df[check].dtypes == "float64":
        return df[to_concat].astype(int).astype(str).T.agg(sep.join)
    else:
        return df[to_concat].astype(str).T.agg(sep.join)


def remove_empty(x):
    """Remove empty strings "-" mainly left after concatenation and fillna operations"""
    x = x.split(", ")
    x = list(
        map(lambda weapon: weapon.replace("-", "") if len(weapon) <= 1 else weapon, x)
    )
    x = list(filter(None, x))
    return ", ".join(x)


def DatetimeToTimestamp(datetime):
    """
    API requires UTC timestamp in milliseconds for the end/{end}/ path variable

    Parameters
    ----------
    date : datetime
        datetime(yyyy, mm, dd)

    Returns
    -------
    int
        UTC timestamp (milliseconds)

    """

    date = datetime.now(timezone.utc)

    return int(date.timestamp() * 1000)


def TimestampToDatetime(timestamp):
    """
    API requires UTC timestamp in milliseconds for the end/{end}/ path variable

    Parameters
    ----------
    date : int
        timestamp

    Returns
    -------
    datetime
        datetime Object

    """

    return datetime.fromtimestamp(timestamp)
