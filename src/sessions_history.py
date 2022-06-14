import pandas as pd
from src.decorators import br_only


""" 
Inside
------
Shape our matches stats history as a session(s) history with aggregated stats per session.

- Before that, ou API output (matches history) was already converted to a df, flattened and formated to be readable / operable (using api_format module)
- We define a session as one or several consecutive matches when idle time between two consecutives match is > 1 hour
- Perform data aggregations per session
- The transformed data will then be displayed in Streamlit where we will eventually apply our rendering tweaks
"""


def add_sessions(df):
    """Add a col "session" with incremental number when duration between 2 games exceed 1 hour"""

    df["session"] = (df["utcEndSeconds"].diff().dt.total_seconds() < -3600).cumsum() + 1
    return df


@br_only
def to_core(df, CONF):
    """Retain core data (columns) only, remove non Battle Royale Matches if told so (@decorator)"""

    cols = CONF.get("APP_DISPLAY").get("cols")["sessions_history"]
    if "session" in df.columns.tolist():
        keep_cols = ["session"]  # prevent modifying CONF recursively
        keep_cols.extend(cols)
    else:
        keep_cols = cols

    return df[keep_cols]


def to_history(df, CONF, LABELS):
    """Pipe the functions above to get our desired sessions history"""
    df = df.pipe(add_sessions).pipe(to_core, CONF)

    return df


def stats_per_session(df):
    """Calculation of aggregated KPIs (kill/death ratio, gulag win ratio etc..) per session

    Will later be rendered in our Streamlit App along side of every session (of n matches)

    Parameters
    ----------
    history : single dataframe with matches as rows, numbered with session id, after to_history was applied

    Returns
    -------
    Dict: aggregated kpis per n session, formatted as :
        {
            session_id_1: {
                "utcEndSeconds": timestamp,
                'kills':total n kills that day,
                'deaths': total deaths,
                'kdRatio': kills/deaths,
                'gulagStatus': win % ,
                'played': count matches
                }
            session_id_2: {...}
        }
    """

    aggregations = {
        "utcEndSeconds": "first",
        "mode": "count",
        "kills": "sum",
        "deaths": "sum",
        "assists": "sum",
        "gulagStatus": lambda x: (x.eq("W").sum() / x.isin(["W", "L"]).sum())
        if x.eq("W").sum() > 0
        else 0,
    }

    df = df.groupby("session").agg(aggregations).rename(columns={"mode": "played"})
    df["kdRatio"] = df.kills / df.deaths

    return df.to_dict(orient="index")
