import utils
import api_format


def get_placement(df, gamertag):
    """--> int, Retrieve final placement of a player/his team"""
    return df[df["Username"] == gamertag]["#"].tolist()[0]


def get_player_kills(df, gamertag):
    """--> dict, Retrieve given Player KD, Kills, Deaths"""
    return df[df["Username"] == gamertag][["KD", "Kills", "Deaths"]].to_dict("records")[
        0
    ]


def teamKills(df, gamertag):
    """Return a DataFrame with Team players and team total KD, K/D/A ; also Loadouts"""

    team = utils.get_team(df, gamertag)
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
        df_team[col] = df_team[col].map(lambda x: api_format.parse_loadout(x))
    return df_team


def teamPercentageKills(df, gamertag):
    team = utils.get_team(df, gamertag)
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
    condition = index["Team"] == utils.get_team(df, gamertag)
    return index[condition]["Kills"].index.tolist()[0]


def topPlayers(df):
    """Return a DataFrame with match top 5 players ranked by Kills, KD"""
    keep_cols = ["Username", "Team", "KD", "Kills", "Deaths", "Assists"] + df.columns[
        df.columns.str.startswith("Loadout")
    ].tolist()
    df_top = df.sort_values(by="Kills", ascending=False)[0:5][keep_cols]

    for col in df_top.columns[df_top.columns.str.startswith("Loadout")]:
        df_top[col] = df_top[col].map(lambda x: api_format.parse_loadout(x))
    return df_top


def playersQuartiles(df):
    """--> dict, All players quartiles (+ mean) that match for Kills and KD"""
    return df[["Kills", "KD"]].describe().to_dict()
