from multiprocessing.reduction import DupFd
import pandas as pd

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

    columns = kwargs.get("columns", ["kdRatio", "kills", "damageDone"])
    for col in columns:
        df[f"{col}CumAvg"] = df[col].expanding().mean()
    return df


def add_moving_avg(df, **kwargs):
    """Compute rolling/moving avg to one or several column"""

    columns = kwargs.get("columns", ["kdRatio", "kills", "damageDone"])
    window = kwargs.get("window", 3)

    for col in columns:
        df[f"{col}RollAvg"] = df[col].rolling(window).mean().round(2)
    return df


def add_gulag_pct(df):
    """Categorical col 'gulagStatus' either W or L : compute Gulag cumulative Win Pct"""

    # cumulative count of "W" * 100 / cumulative sum of rows
    df["W_cum_count"] = df["gulagStatus"].eq("W").cumsum()
    df["rows_count"] = df.index  # we already sorted/reindexed it w/ add_sorted_index
    df["gulagWinPct"] = df["W_cum_count"] * 100 / df["rows_count"]
    return df


def to_history(df, **kwargs):
    """Pipe the functions above to get our desired "time" series"""

    df = (
        df.pipe(add_sorted_index)
        .pipe(add_cumulative_avg)
        .pipe(add_moving_avg)
        .pipe(add_gulag_pct)
    )

    return df
