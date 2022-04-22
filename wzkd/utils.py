import datetime
from datetime import datetime, timezone
from doctest import DocFileTest
import pandas as pd
import numpy as np
import toml
import json

# CONF utils


def load_labels(file="wz_labels.json"):
    """--> dict, with data needed to parse weapons, games modes etc."""
    with open(file) as f:
        LABELS = json.load(f)
    return LABELS


def load_conf(file="conf.toml"):
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


def get_gamer_tag(matches):
    """
    A player can be searchable with a given name but having a different gamertag in-game
    We need that gamertag if we were to analyse the "one match stats" endpoint (as done in match_format.py)
    from player's perspective
    """
    return matches[0]["player"]["username"]


def get_team(df, gamertag):
    """--> str, Retrieve team name of given gamertag"""
    return df[df["Username"] == gamertag]["Team"].tolist()[0]


def get_teammates(df, gamertag):
    """--> list(str), Retrieve list of gamertag + his teammates"""
    team = get_team(df, gamertag)
    return df[df["Team"] == team]["Username"].tolist()


def get_date(df):
    """--> str, Retrieve end date (str) of our match"""
    return df["Ended at"][0].strftime("%Y-%m-%d %H:%M")


def get_mode(df):
    """--> str, retrieve BR type of our match"""
    return df["Mode"][0]


# formatting tools


def shrink_df(df, cols_to_concat, str_join, new_col):
    """For our df to occupy less space in Streamlit : to str + concat given cols into 1"""

    def concat_cols(df, cols_to_concat, str_join):
        return pd.Series(
            map(str_join.join, df[cols_to_concat].values.tolist()), index=df.index
        )

    for col in cols_to_concat:
        df[col] = df[col].astype(str)
    df[new_col] = concat_cols(df, cols_to_concat, str_join)
    df = df.drop(cols_to_concat, axis=1)

    return df


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
