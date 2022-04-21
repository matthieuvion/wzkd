import datetime
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from itertools import product
from utils import load_conf, load_labels, extract_loadouts, parse_loadout, parse_gulag


def retrieveTeam(df, gamertag):
    """--> str, Retrieve team name of given gamertag"""
    return df[df["Username"] == gamertag]["Team"].tolist()[0]


def retrieveTeammates(df, gamertag):
    """--> list(str), Retrieve list of gamertag + his teammates"""
    team = retrieveTeam(df, gamertag)
    return df[df["Team"] == team]["Username"].tolist()


def retrieveDate(df):
    """--> str, Retrieve end date (str) of our match"""
    return df["Ended at"][0].strftime("%Y-%m-%d %H:%M")


def retrieveMode(df):
    """--> str, retrieve BR type of our match"""
    return df["Mode"][0]


def retrievePlacement(df, gamertag):
    """--> int, Retrieve final placement of a player/his team"""
    return df[df["Username"] == gamertag]["#"].tolist()[0]


def retrievePlayerKills(df, gamertag):
    """--> dict, Retrieve given Player KD, Kills, Deaths"""
    return df[df["Username"] == gamertag][["KD", "Kills", "Deaths"]].to_dict("records")[
        0
    ]


def teamKills(df, gamertag):
    """Return a DataFrame with Team players and team total KD, K/D/A ; also Loadouts"""

    team = retrieveTeam(df, gamertag)
    keep_cols = ["Username", "KD", "Kills", "Deaths", "Assists"] + df.columns[
        df.columns.str.startswith("Loadout")
    ].tolist()
    df_team = df[df["Team"] == team][keep_cols].sort_values("Kills", ascending=False)

    # add Team aggregated stats final row
    agg_func = {"KD": "sum", "Kills": "sum", "Deaths": "sum", "Assists": "sum"}

    team_kd = (df_team.Kills.sum() / df_team.Deaths.sum()).round(1)
    row_total = df_team.agg(agg_func).to_dict()

    row_total.update({"Username": "Team"})
    row_total.update({"KD": team_kd})
    df_team = df_team.append(row_total, ignore_index=True)
    df_team[["Kills", "Deaths", "Assists"]] = df_team[
        ["Kills", "Deaths", "Assists"]
    ].astype(int)
    df_team.fillna("-", inplace=True)

    # Convert COD weapons code names, using labels.py , parse_weapons()
    for col in df_team.columns[df_team.columns.str.startswith("Loadout")]:
        df_team[col] = df_team[col].map(lambda x: parse_weapons(x))
    return df_team


def teamPercentageKills(df, gamertag):
    team = retrieveTeam(df, gamertag)
    tkills = df[df["Team"] == team].Kills.sum()
    gkills = df.Kills.sum()
    return ((tkills * 100) / gkills).round(1)


def teamKillsPlacement(df, gamertag):
    """Retrieve final placement according to # kills, of a player/his team"""
    index = (
        df.groupby("Team")[["Kills"]]
        .sum()
        .sort_values("Kills", ascending=False)
        .reset_index()
    )
    condition = index["Team"] == retrieveTeam(df, gamertag)
    return index[condition]["Kills"].index.tolist()[0]


def topPlayers(df):
    """Return a DataFrame with match top 5 players ranked by Kills, KD"""
    keep_cols = ["Username", "Team", "KD", "Kills", "Deaths", "Assists"] + df.columns[
        df.columns.str.startswith("Loadout")
    ].tolist()
    df_top = df.sort_values(by="Kills", ascending=False)[0:5][keep_cols]

    for col in df_top.columns[df_top.columns.str.startswith("Loadout")]:
        df_top[col] = df_top[col].map(lambda x: parse_weapons(x))
    return df_top


def playersQuartiles(df):
    """--> dict, All players quartiles (+ mean) that match for Kills and KD"""
    return df[["Kills", "KD"]].describe().to_dict()


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
