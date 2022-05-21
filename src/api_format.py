import datetime
from datetime import datetime, timezone
from doctest import DocFileCase
import pandas as pd
import numpy as np
from itertools import product
from src.utils import load_conf, load_labels


""" 
Inside
------
Module overall purpose is to flatten COD API matche(s) result to a maximum, into a DataFrame
Then make data readable & useable for future display / aggregations
"""


def extract_loadouts(df, CONF):
    """
    Extract player(s) loadout(s) from match(es) df > player col > 'loadout' (or 'loadouts')
    Flatten (breakdown) them into one or several cols : one for every loadout
    n of loadouts to extract defined in conf.toml

    Parameters
    ----------
    df, match result previously converted as a df, with 'player' col already expanded

    Returns
    -------
    Dataframe, with n columns of players loadout(s), that we will append to our main df
    """

    loadout_col = "loadout" if "loadout" in df.columns.tolist() else "loadouts"
    # when extracting, df 'player' col is already expanded, with 'loadout' accessible
    df_loadouts = df[loadout_col].apply(pd.Series)

    # max number of payloads to parse, as defined in conf
    n_loadouts = CONF.get("API_OUTPUT_FORMAT")["n_loadouts"]
    n_loadouts = (
        n_loadouts
        if n_loadouts <= len(df_loadouts.columns)
        else len(df_loadouts.columns)
    )

    # remove the extra loadouts ( > max loadouts to keep)
    df_loadouts = df_loadouts.iloc[:, 0:n_loadouts]

    # rename final columns : loadout_1, loadout_2 ...
    col_names = {idx: f"loadout_{idx+1}" for idx, col in enumerate(df_loadouts.columns)}
    df_loadouts.rename(columns=col_names, inplace=True)

    return df_loadouts


def parse_loadout(loadout_value, LABELS):
    """
    Parse a loadout entry (dict),  extract weapons names then rename using wzlabels.json

    Parameters
    ----------
    loadout : a dict value after we flattened a match(es) result / extracted loadouts entries.
        e.g.
        dict{
                primaryWeapon:{name:s4_pi_mike1911...},
                perks:[...],
                other keys,,
            }

    Returns
    -------
    String, parsed primary and secondary weapons names
    """

    def extract_weapons(loadout_value):
        return f"{loadout_value.get('primaryWeapon')['name']} {loadout_value.get('secondaryWeapon')['name']}"

    def parse_weapons(weapons, LABELS):
        list_weapons = weapons.split(" ")
        for PREFIX in LABELS["weapons"].get("prefixes"):
            list_weapons = list(
                map(lambda weapon: weapon.replace(PREFIX, ""), list_weapons)
            )
        list_weapons = [
            weapon.replace(weapon, LABELS["weapons"]["names"].get(weapon, weapon))
            for weapon in list_weapons
        ]
        return " ".join(list_weapons)

    if pd.isnull(loadout_value):
        return np.nan
    else:
        weapons = extract_weapons(loadout_value)
        return parse_weapons(weapons, LABELS)


def extract_missions(df):
    """
    Flatten then extract (desired) mission stats from matche(s) df > player col > 'brMissionStats'

    Parameters
    ----------
    df, match(es) result previously converted as a df, with 'player'/' col already expanded

    Returns
    -------
    Dataframe, with desired missions KPIs as columns, that we will append to our main df
    """

    main_col = "brMissionStats"
    sub_col = "missionStatsByType"
    df_missions = df[main_col].apply(pd.Series)

    return pd.concat(
        [df_missions.drop([sub_col], axis=1), df_missions[sub_col].apply(pd.Series)],
        axis=1,
    )


def parse_mission(mission_value):
    """
    Parse a mission entry (dict), extracting 'count'

    Parameters
    ----------
    mission_value : a dict value after we flattened a match(es) result/'player'/'brMissionStats'
        e.g.
        dict{
                weaponXp:650.0},
                xp:650,
                count:1
            }

    Returns
    -------
    int, count of a given mission
    """

    if pd.isnull(mission_value):
        return np.nan
    else:
        return mission_value["count"]


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

    # Make timestamps (start/end times of a match) and durations/length readable
    for ts_col in CONF["API_OUTPUT_FORMAT"]["ts_cols"]:
        df[ts_col] = df[ts_col].apply(lambda x: datetime.fromtimestamp(x))
    df["duration"] = (
        df["duration"]
        .apply(lambda x: x / 1000)
        .apply(lambda x: pd.to_datetime(x, unit="s").strftime("%M"))
    )  # API duration is in seconds x1000
    df["timePlayed"] = df["timePlayed"].apply(
        lambda x: pd.to_datetime(x, unit="s").strftime("%M:%S")
    )  # API timePlayed is in seconds

    # Loadouts/weapons : extract then parse weapons from loadout(s) cols
    loadout_cols = [col for col in df.columns if col.startswith("loadout_")]
    if loadout_cols:
        for col in loadout_cols:
            df[col] = df[col].apply(
                lambda x: parse_loadout(x, LABELS) if not str(x) == "nan" else np.nan
            )

    # Missions types : extract count
    for mission_col in LABELS.get("missions")["types"]:
        if mission_col in df.columns.tolist():
            df[mission_col] = (
                df[mission_col]
                .apply(lambda x: parse_mission(x) if not str(x) == "nan" else np.nan)
                .astype("Int64")
            )

    # parse game modes (either battle royale : duos..., or 'multiplayer : plunder, rebirth island...)
    for mode in list(LABELS.get("modes").keys()):
        df = df.replace({"mode": LABELS.get("modes")[mode]})

    return df


def add_gulag_status(df, LABELS):
    """
    Add a new column 'gulagStatus', giving 'gulagKills' & 'gulagDeaths' entries

    Note:
    -----
    Re. Gulag,  API has some discrepancies ; at least to me ^_^
    But 99% of time, our returned gulagStatus will reflect what happened in-game
    """

    # Non BR modes should always return NaN (or nothing) for GulagDeaths and GulagKills
    # However there are inconsistencies : some non BR mode (e.g Caldera Clash) still returns 0.
    if "gulagKills" in df.columns.tolist():
        df.loc[
            df["mode"].isin(list(LABELS.get("modes")["multiplayer"].values())),
            ["gulagKills", "gulagDeaths"],
        ] = np.nan

        filters = [
            # Modes without a gulag (e.g Plunder)
            (df.gulagKills.isnull()),
            # sometimes API returns both 1 kill and 1 death...maybe we still die after we got the kill ?
            (df.gulagKills == 1) & (df.gulagDeaths == 1),
            # Flag victory
            (df.gulagKills == 0) & (df.gulagDeaths == 0),
            # We killed the poor guy :
            (df.gulagKills == 1) & (df.gulagDeaths == 0),
            # We got killed.
            # Not sure why deaths can be > 1 (even in non multi gulag modes)
            # whereas kills seems to be always 1 or 0. Maybe team count
            (df.gulagKills == 0) & (df.gulagDeaths >= 1),
        ]
        values = [0, "W", "W", "W", "L"]

        df["gulagStatus"] = np.select(filters, values, default=np.nan)
        # Cant cast np.nan witk np.select so we used "0" and convert it back to NaN
        df["gulagStatus"] = df["gulagStatus"].replace("0", np.nan)

    return df


def augment_df(df, LABELS):
    """Pipe the functions above to transform/add new KPIs"""
    df = df.pipe(add_gulag_status, LABELS)

    return df
