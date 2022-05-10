import pandas as pd
from decorators import br_only


""" 
Inside
------
Matches :
- Output was already converted to a df, flattened and formated to be readable / operable
- Convert (list of) matches to (list of) matches per session
- Perform data aggregations per session
- Send back this transformed data to Streamlit where we will eventually apply our rendering tweaks
"""


def add_sessions(df):
    """Add a col "session" with incremental number when duration beteween 2 games exceed 1 hour"""

    df["session"] = (df["utcEndSeconds"].diff().dt.total_seconds() < -3600).cumsum() + 1
    return df


@br_only
def to_core(df, CONF, LABELS):
    """Retain core data (columns) only, remove non Battle Royale Matches if told so (@decorator)"""

    cols = CONF.get("APP_DISPLAY").get("cols")["history"]
    if "session" in df.columns.tolist():
        keep_cols = ["session"]  # prevent modifying CONF recursively
        keep_cols.extend(cols)
    else:
        keep_cols = cols

    return df[keep_cols]


def to_history(df, CONF, LABELS):
    """Pipe the functions above to get our desired matches history"""
    history = df.pipe(add_sessions).pipe(to_core, CONF, LABELS)

    return history


def stats_per_session(history):
    """
    Calculation of aggregated KPIs (kill/death ratio, gulag win ratio etc..) per session
    Will later be rendered in our Streamlit App on top of every session of matches

    Parameters
    ----------
    history : single dataframe with matches as rows, numbered with session id, after to_history was applied

    Returns
    -------
    Dict: aggregated kpis per session, formatted as :
        {
            session_id: {
                "utcEndSeconds": timestamp,
                'kills':total n kills that day,
                'deaths': total deaths,
                'kdRatio': kills/deaths,
                'gulagStatus': win % ,
                'played': count matches
                }
            session_id: {...}
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

    agg_history = (
        history.groupby("session").agg(aggregations).rename(columns={"mode": "played"})
    )
    agg_history["kdRatio"] = agg_history.kills / agg_history.deaths

    return agg_history.to_dict(orient="index")


# A TRANSFERER POUR PARTIE DANS STREAMLIT
def to_sessions(df):
    """
    Final layer applied to our list of matches with stats, to render them in our Streamlit App
    Streamlit/basic AgGrid does not render well (aka w. blank rows etc.) multi indexed df
    So we structure and display our data differently : one df => dfs grouped by session

    Returns
    -------
    Dictionary :
    {
        "str_session_time":df-with-matches-that-session,
        "str_session_time":df-with-matches-that-session,
        (...)
    }
    """

    drop_cols = ["Started at", "Playtime", "% moving", "Game duration"]

    keep_cols = [
        "utcEndSeconds",
        "mode",
        "teamPlacement",
        "kdRatio",
        "kills",
        "deaths",
        "assists",
        "damageDone",
        "damageReceived",
        "gulagKills",
    ]

    loadout_cols = df.columns[df.columns.str.startswith("Loadout")].tolist()
    df[loadout_cols] = df[loadout_cols].replace(
        0, "-"
    )  # else can't concat Loadouts cols

    # 1. --- initial formating : datetime, concat loadouts cols ---

    df = df.drop(drop_cols, axis=1)
    df["utcEndSeconds"] = df["utcEndSeconds"].dt.time

    def concat_loadouts(df, columns):
        return pd.Series(map(" , ".join, df[columns].values.tolist()), index=df.index)

    df["weapons"] = concat_loadouts(df, loadout_cols)
    keep_cols = [*keep_cols, *["weapons"]]

    # 2. --- build result {"day1": df-matches-that-day, "day2": df...} ---

    list_df = [g for n, g in df.groupby(pd.Grouper(key="utcEndSeconds", freq="D"))]
    list_df = [df for df in list_df if not df.empty]
    list_days = [
        df["utcEndSeconds"].tolist()[0].strftime("%Y-%m-%d (%A)") for df in list_df
    ]

    # make sure we display latest day first, then build dictionary
    for list_ in [list_days, list_df]:
        list_.reverse()
    day_matches = dict(zip(list_days, list_df))

    # 3. --- some more (re)formating ---

    # for some reason (me ? ^-^, Grouper => Series?) couldnt' modify df before building the result, must iterate again
    for k, v in day_matches.items():
        day_matches[k] = day_matches[k][keep_cols]

    return day_matches


def daily_stats(df):
    """
    We want to add aggregated stats for each day/df of matches we got from MatchesPerDay()
    Each daily aggregation will be rendered in our Streamlit App on top of each list of matches

    Returns
    -------
    Dictionary :
    {
    'kills':total n kills that day,
    'deaths': total deaths,
    'kdRatio': kills/deaths,
    'gulagkills': win % ,
    'played': count matches -
    }
    """

    agg_func = {"mode": "count", "kills": "sum", "deaths": "sum"}

    kd = (df.Kills.sum() / df.Deaths.sum()).round(2)
    gulagWinRatio = int((df.Gulag.str.count("W").sum() * 100) / len(df))

    dict_ = df.agg(agg_func).to_dict()
    dict_.update({"kdRatio": kd})
    dict_.update({"gulagKills": gulagWinRatio})
    dict_["played"] = dict_.pop("mode")

    return dict_
