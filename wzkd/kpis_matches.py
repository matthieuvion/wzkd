import pandas as pd


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


def daily_stats(df):
    """
    We want to add aggregated stats for each day/df of matches we got from MatchesPerDay()
    Each daily aggregation will be rendered in our Streamlit App on top of each list of matches

    Returns
    -------
    Dictionary :
    {
    'Kills':total n kills that day,
    'Deaths': total deaths,
    'KD': kills/deaths,
    'Gulags': win % ,
    'Played': count matches -
    }
    """

    agg_func = {"Mode": "count", "Kills": "sum", "Deaths": "sum"}

    kd = (df.Kills.sum() / df.Deaths.sum()).round(2)
    gulagWinRatio = int((df.Gulag.str.count("W").sum() * 100) / len(df))

    dict_ = df.agg(agg_func).to_dict()
    dict_.update({"KD": kd})
    dict_.update({"Gulags": gulagWinRatio})
    dict_["Played"] = dict_.pop("Mode")

    return dict_
