import pandas as pd

from src import kd_history

""" 
Inside
------
Light time series treatment(s) on some Warzone historical KPIs like Kills/Deaths ratio (KD)

- Before that we collected a matches history
- Also our API output (detailed matches stats) was already converted to a df, flattened and formated to be readable / operable (using api_format module)
- 
"""


def add_sorted_index(df):
    """Make sure our matches history is sorted from least recent to last"""

    df = df.sort_values(by="utcStartSeconds", ascending=True).reset_index(drop=True)
    return df


def add_cumulative_avg(df, **kwargs):
    """Compute cumulative ("incremental") avg to one or several column"""

    columns = kwargs.get("columns", ["kills", "damageDone"])
    for col in columns:
        df[f"{col}CumAvg"] = df[col].expanding().mean()
    return df


def add_moving_avg(df, **kwargs):
    """Compute rolling/moving avg to one or several column"""

    columns = kwargs.get("columns", ["kdRatio", "kills", "damageDone"])
    window = kwargs.get("window", 5)

    for col in columns:
        df[f"{col}RollAvg"] = df[col].rolling(window, min_periods=1).mean().round(2)
    return df


def add_cumulative_kd(df):
    """Compute k/d ratio over cumsum (cumulative) kills / deaths"""

    # cumulative sum of kills  / cumulative sum of deaths
    df["kills_cumsum"] = df["kills"].cumsum()
    df["deaths_cumsum"] = df["deaths"].cumsum()
    df["kdRatioCum"] = df["kills_cumsum"] / df["deaths_cumsum"]
    return df


def add_gulag_pct(df):
    """Categorical col 'gulagStatus' either W or L : compute Gulag cumulative Win Pct"""

    # cumulative count of "W" * 100 / cumulative sum of rows
    df["W_cumsum"] = df["gulagStatus"].eq("W").cumsum()
    df["rows_count"] = df.index  # we already sorted/reindexed it w/ add_sorted_index
    df["gulagWinPct"] = df["W_cumsum"] * 100 / df["rows_count"]
    return df


def extract_last_cum_kd(data):
    """
    Extract last cum kd from br, resu, others last recent matches
    """
    cum_kd = dict()
    for label in ["Battle Royale", "Resurgence", "Others"]:
        if len(data.get(label)) >= 1:
            df_cum_kd = kd_history.add_cumulative_kd(data.get(label))
            cum_kd[label] = round(df_cum_kd["kdRatioCum"].tolist()[-1], 2)
        else:
            cum_kd[label] = 1

    return cum_kd


def to_history(df, **kwargs):
    """Pipe the functions above to get our desired "time" series"""

    df = (
        df.pipe(add_sorted_index)
        .pipe(add_cumulative_avg)
        .pipe(add_moving_avg)
        .pipe(add_cumulative_kd)
        .pipe(add_gulag_pct)
    )

    return df
