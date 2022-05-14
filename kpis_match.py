import utils
import api_format


def get_placement(df, gamertag):
    """--> int, Retrieve final placement of a player/his team"""
    return df[df["username"] == gamertag]["teamPlacement"].tolist()[0]


def get_player_kills(df, gamertag):
    """--> dict, Retrieve given Player KD, Kills, Deaths"""
    return df[df["username"] == gamertag][["kdRatio", "kills", "deaths"]].to_dict(
        "records"
    )[0]


def teamKills(df, gamertag, LABELS):
    """Return a DataFrame with Team players and team total KD, K/D/A ; also Loadouts"""

    team = utils.get_team(df, gamertag)
    keep_cols = ["username", "kdRatio", "kills", "deaths", "assists"] + df.columns[
        df.columns.str.startswith("loadout")
    ].tolist()
    df_team = df[df["team"] == team][keep_cols].sort_values("kills", ascending=False)

    # add Team aggregated stats final row
    agg_func = {"kdRatio": "sum", "kills": "sum", "deaths": "sum", "assists": "sum"}

    team_kd = (df_team.kills.sum() / df_team.deaths.sum()).round(1)
    row_total = df_team.agg(agg_func).to_dict()

    row_total.update({"username": "team"})
    row_total.update({"kdRatio": team_kd})
    df_team = df_team.append(row_total, ignore_index=True)
    df_team[["kills", "deaths", "assists"]] = df_team[
        ["kills", "deaths", "assists"]
    ].astype(int)
    df_team.fillna("-", inplace=True)

    # Convert COD weapons code names, using labels.py , parse_weapons()
    for col in df_team.columns[df_team.columns.str.startswith("loadout")]:
        df_team[col] = df_team[col].map(lambda x: api_format.parse_loadout(x, LABELS))
    return df_team


def teamPercentageKills(df, gamertag):
    team = utils.get_team(df, gamertag)
    tkills = df[df["team"] == team].kills.sum()
    gkills = df.kills.sum()
    return ((tkills * 100) / gkills).round(1)


def teamKillsPlacement(df, gamertag):
    """Retrieve final placement according to # kills, of a player/his team"""
    index = (
        df.groupby("team")[["kills"]]
        .sum()
        .sort_values("kills", ascending=False)
        .reset_index()
    )
    condition = index["team"] == utils.get_team(df, gamertag)
    return index[condition]["kills"].index.tolist()[0]


def topPlayers(df, LABELS):
    """Return a DataFrame with match top 5 players ranked by Kills, KD"""
    keep_cols = [
        "username",
        "team",
        "kdRatio",
        "kills",
        "deaths",
        "assists",
    ] + df.columns[df.columns.str.startswith("loadout")].tolist()
    df_top = df.sort_values(by="kills", ascending=False)[0:5][keep_cols]

    for col in df_top.columns[df_top.columns.str.startswith("loadout")]:
        df_top[col] = df_top[col].map(lambda x: api_format.parse_loadout(x, LABELS))
    return df_top


def playersQuartiles(df):
    """--> dict, All players quartiles (+ mean) that match for Kills and KD"""
    return df[["kills", "kdRatio"]].describe().to_dict()
