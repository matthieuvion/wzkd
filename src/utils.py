from pathlib import Path
import datetime
from datetime import datetime, timezone

from typing import Literal
import pandas as pd
import toml
import json

# CONF utils


def load_labels():
    """--> dict, with data needed to parse weapons, games modes etc."""

    filepath = Path.cwd() / "src" / "wz_labels.json"
    # use case, @decorator fails to import when executed from notebooks/
    if not filepath.is_file():
        filepath = Path.cwd().parent / "src" / "wz_labels.json"

    with open(filepath) as f:
        LABELS = json.load(f)
    return LABELS


def load_conf():
    """--> dict, overall app config : run in offline mode, display Battle Royale games only etc."""

    filepath = Path.cwd() / "src" / "conf.toml"
    # use case, @decorator fails to import when executed from notebooks/
    if not filepath.is_file():
        filepath = Path.cwd().parent / "src" / "conf.toml"

    with open(filepath) as f:
        CONF = toml.load(f)
    return CONF


def filter_history(
    recent_matches, LABELS, select: Literal["Battle Royale", "Resurgence", "Others"]
):
    """Filter --an already parsed/formated) recent matches history, retain either
    BR, Resurgence or Others match type"""

    if select == "Battle Royale":
        list_modes = list(LABELS.get("modes").get("battle_royale").values())
    elif select == "Resurgence":
        list_modes = list(LABELS.get("modes").get("resurgence").values())
    elif select == "Others":
        list_modes = list(LABELS.get("modes").get("others").values())

    return recent_matches.query("mode in @list_modes")


def get_last_session_ids(matches):
    """Extract match ids, from last session matches, out of a single (last played) match type (br OR resu)"""

    # Add a col "session" with incremental number when duration between 2 games exceed 1 hour
    df_matches = pd.DataFrame(matches)[["utcEndSeconds", "mode", "matchID"]]
    df_matches["utcEndSeconds"] = df_matches["utcEndSeconds"].apply(
        lambda x: datetime.fromtimestamp(x)
    )
    df_matches["session"] = (
        df_matches["utcEndSeconds"].diff().dt.total_seconds() < -3600
    ).cumsum() + 1

    df_matches = df_matches.query(
        "`mode`.str.contains('br_br') or `mode`.str.contains('br_rebirth')"
    )
    session_min_idx = df_matches.session.min()
    last_type_selector = df_matches["mode"].tolist()[0]
    last_type_selector = (
        "br_br" if not "rebirth" in last_type_selector else "br_rebirth"
    )
    match_ids = (
        df_matches.query("`mode`.str.contains(@last_type_selector)")
        .groupby("session")
        .get_group(session_min_idx)
        .matchID.tolist()
    )
    return [int(br_id) for br_id in match_ids]


def get_gamertag(matches):
    """
    A player can be searchable with a given name but having a different gamertag in-game
    Because you can change your gamertag and choose something different than your "main profile"
    If you want to analyse data from player's / his team perspective, gamertag could be retrieved
    from recent matches (history) endpoint.
    """
    isDataframe = isinstance(matches, pd.DataFrame)
    if isDataframe:
        return matches["username"][0]
    else:
        return matches[0]["player"]["username"]


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
