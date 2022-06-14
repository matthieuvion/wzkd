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
    """Compute cumulative ("incremental") average to the selected kpis (columns)"""

    columns = kwargs.get("columns", ["kdRatio", "kills"])
    for col in columns:
        df[f"{col}CumAvg"] = df[col].expanding().mean()
    return df


def to_history(df, **kwargs):
    """Pipe the functions above to get our desired "time" series"""

    df = df.pipe(add_sorted_index).pipe(add_cumulative_avg)

    return df
