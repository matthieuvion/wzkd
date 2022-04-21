import datetime
from datetime import datetime, timezone
from doctest import DocFileCase
import pandas as pd
import numpy as np
from itertools import product
from utils import (
    load_conf,
    load_labels,
    extract_loadouts,
    parse_loadout,
    parse_gulag,
    extract_missions,
    parse_mission,
)


""" 
Inside
------
Module overall purpose is to flatten COD API matche(s) result to a maximum, in a DataFrame
Then makes data readable & useable for future display / operations
"""


def res_to_df(res, CONF):
    """
    Convert Match or Matches API result to a DataFrame we can perform our aggregations nicely, later.
    Built mainly to analyze a 'Battle Royale' match, but should work with other modes without too many modifs
    Expand (flatten) most entries. I.e 'player & 'playerstats' that have multiple levels; including loadout(s)

    Parameters
    ----------
    Either:
    match : result from COD API "match" endpoint ; FYI formatted as :
        list[
                dict{ player 1 match stats },
                dict{ player 2 match stats },
                dict{ +- 150 players },
            ]


    matches : result from COD API "matches" endpoint ; FYI formatted as :
        list[
                dict{ match 1 stats },
                dict{ match 2 stats },
                dict{ 20 matches max },
            ]

    Returns
    -------
    DataFrame,
    Either:
    Match : every player of a given match as rows, matches/player stats this given match as columns/values
    Matches : every match of a list of matches as rows, a given player stats for every match as columns/values
    """

    df = pd.DataFrame(res)

    # cols 'playerStats' (1) and 'player' (2) can be expanded further

    # 1. playerStats' contains dict entries (kills, team placement...)
    df = pd.concat(
        [df.drop(["playerStats"], axis=1), df["playerStats"].apply(pd.Series)], axis=1
    )

    # 2. 'player' has more depth. Once expanded (also) contains 'loadout' (a) and possibly 'brMissionStats' (b)
    df = pd.concat([df.drop(["player"], axis=1), df["player"].apply(pd.Series)], axis=1)

    # 2a. 'player'/'loadout' (and/or 'loadouts', same data) is a Series of list of dict
    # We expand it to one or several cols, then parse weapons names (extract)
    loadout_cols = [col for col in df.columns if col.startswith("loado")]
    loadout_col = "loadout" if "loadout" in loadout_cols else "loadouts"
    df = pd.concat([df.drop(loadout_cols, axis=1), extract_loadouts(df, CONF)], axis=1)

    # 2b. 'player'/'brMissionStats', may not be returned for other game modes than BR, is a Series of dict (with dict)
    if "brMissionStats" in df.columns.tolist():
        df = pd.concat(
            [df.drop(["brMissionStats"], axis=1), extract_missions(df)], axis=1
        )

    #### final

    # after we flattened all the entries, columns with nulls can exist (e.g in 'brmissionstats'),
    # also the final result may contain duplicate entries, most probably "rank" that's returned twice by the API
    df.dropna(axis=1, how="all", inplace=True)
    df = df.loc[
        :, ~df.columns.duplicated()
    ]  # gl trying to remove dup cols in Pandas (if any col is a dict) ^_^

    return df


def format_df(df, CONF, LABELS):
    """
    Add a first layer of standadization (as : properly formatted) to our matches/match DataFrame
    For better readibility of API data and future aggregations we will carry on.
    Among others :
    - convert timestamps and durations for human readability
    - parse weapons and game modes names, using wz_labels.json
    - first layer of simplification to our numerical values (int as int, round floats values...)
    - convert gulagKills to W or L

    Parameters
    ----------
    DataFrame, match or matches result as flattened and converted in to_df()

    Returns
    -------
    DataFrame,
    Either:
    Match (formatted) : every player of a given match as rows, matches/player stats this given match as columns/values
    Matches (formatted) : every match of a list of matches as rows, a given player stats for every match as columns/values
    """

    # Some int cols like gulagKills or teamPlacement do not exist if the mode =/ Battle Royale
    # Also we're using Int64, to preserve NaN values and not throwing an error when casting ints
    int_cols = [
        col for col in CONF["FORMATTING"]["int_cols"] if col in df.columns.tolist()
    ]
    df[int_cols] = df[int_cols].astype("Int64")

    # Round float values. Later on will still renders as 0.0000 in streamlit but an ugly hacks exists
    df[CONF["FORMATTING"]["float_cols"]] = (
        df[CONF["FORMATTING"]["float_cols"]].astype(float).round(1)
    )

    # Make timestamps (start/end times of a match) and durations/length readable
    for ts_col in CONF["FORMATTING"]["ts_cols"]:
        df[ts_col] = df[ts_col].apply(lambda x: datetime.fromtimestamp(x))
    df["duration"] = (
        df["duration"]
        .apply(lambda x: x / 1000)
        .apply(lambda x: pd.to_datetime(x, unit="s").strftime("%M"))
    )  # API duration is in seconds x1000
    df["timePlayed"] = df["timePlayed"].apply(
        lambda x: pd.to_datetime(x, unit="s").strftime("%M:%S")
    )  # API timePlayed is in seconds

    # 'gulagKills' : convert to W(in) or L(osse)
    if "gulagKills" in df.columns.tolist():
        df["gulagKills"] = df["gulagKills"].apply(
            lambda x: parse_gulag(x) if not str(x) == "nan" else np.nan
        )

    # Loadouts/weapons : extract then parse weapons from loadout(s) cols
    loadout_cols = [col for col in df.columns if col.startswith("loadout_")]
    if loadout_cols:
        for col in loadout_cols:
            df[col] = df[col].apply(
                lambda x: parse_loadout(x, LABELS) if not str(x) == "nan" else np.nan
            )

    # Missions types : extract count
    for mission_col in CONF.get("PARSING")["mission_types"]:
        if mission_col in df.columns.tolist():
            df[mission_col] = (
                df[mission_col]
                .apply(
                    lambda x: parse_mission(x, CONF) if not str(x) == "nan" else np.nan
                )
                .astype("Int64")
            )

    # parse game modes (either battle royale : duos..., or 'multiplayer : plunder, rebirth island...)
    for mode in list(LABELS.get("modes").keys()):
        df = df.replace({"mode": LABELS.get("modes")[mode]})

    return df


# st.cache
def matches_per_day(df):
    """
    Final layer applied to our list of matches with stats, to render them in our Streamlit App
    Streamlit/basic AgGrid does not render well (aka w. blank rows etc.) multi indexed df
    So we structure and display our data differently (a dictionary instead of a df), in a daily manner

    Returns
    -------
    Dictionary :
    {
        "str_weekday_1":df-of-matches-that-day,
        "str_weekday_2":df-of-matches-that-day,
        (...)
    }
    """

    drop_cols = ["Started at", "Playtime", "% moving", "Game duration"]

    keep_cols = [
        "End time",
        "Mode",
        "#",
        "KD",
        "Kills",
        "Deaths",
        "Assists",
        "Damage >",
        "Damage <",
        "Gulag",
    ]

    loadout_cols = df.columns[df.columns.str.startswith("Loadout")].tolist()
    df[loadout_cols] = df[loadout_cols].replace(
        0, "-"
    )  # else can't concat Loadouts cols

    # 1. --- initial formating : datetime, concat loadouts cols ---

    df = df.drop(drop_cols, axis=1)
    df["End time"] = df["Ended at"].dt.time

    def concat_loadouts(df, columns):
        return pd.Series(map(" , ".join, df[columns].values.tolist()), index=df.index)

    df["Weapons"] = concat_loadouts(df, loadout_cols)
    keep_cols = [*keep_cols, *["Weapons"]]

    # 2. --- build result {"day1": df-matches-that-day, "day2": df...} ---

    list_df = [g for n, g in df.groupby(pd.Grouper(key="Ended at", freq="D"))]
    list_df = [df for df in list_df if not df.empty]
    list_days = [df["Ended at"].tolist()[0].strftime("%Y-%m-%d (%A)") for df in list_df]

    # make sure we display latest day first, then build dictionary
    for list_ in [list_days, list_df]:
        list_.reverse()
    day_matches = dict(zip(list_days, list_df))

    # 3. --- some more (re)formating ---

    # for some reason (me ? ^-^, Grouper => Series?) couldnt' modify df before building the result, must iterate again
    for k, v in day_matches.items():
        day_matches[k] = day_matches[k][keep_cols]

    return day_matches
