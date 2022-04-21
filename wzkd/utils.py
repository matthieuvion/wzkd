import datetime
from datetime import datetime, timezone
from doctest import DocFileTest
import pandas as pd
import numpy as np
import toml
import json


def load_labels(file="wz_labels.json"):
    """--> dict, with data needed to parse weapons, games modes etc."""
    with open(file) as f:
        LABELS = json.load(f)
    return LABELS


def load_conf(file="conf.toml"):
    """--> dict, overall app config : run in offline mode, display Battle Royale games only etc."""
    with open(file) as f:
        CONF = toml.load(f)
    return CONF


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
    n_loadouts = CONF.get("PARSING")["n_loadouts"]
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


def parse_mission(mission_value, CONF):
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


def parse_gulag(gulagKills):
    """
    Parse a gulagKills entry with a value either NaN, 1 or 0, to W, L, NaN
    """
    if pd.isnull(gulagKills):
        return np.nan
    else:
        return "W" if gulagKills == 1 else "L"


def get_last_match_Id(matches):
    """Extract last (Battle Royale) Match ID from list of last matches"""
    list_br_match = [match for match in matches if "br_br" in match["mode"]]
    last_match_id = int(list_br_match[0]["matchID"]) if len(list_br_match) > 0 else None
    return last_match_id


def get_gamer_tag(matches):
    """
    A player can be searchable with a given name but having a different gamertag in-game
    We need that gamertag if we were to analyse the "one match stats" endpoint (as done in match_format.py)
    from player's perspective
    """
    return matches[0]["player"]["username"]


def DatetimeToTimestamp(datetime):
    """
    API requires UTC timestamp in milliseconds for the end/{end}/ path variable

    Parameters
    ----------
    date : datetime
        datetime(yyyy, mm, dd)

    Returns
    -------
    int
        UTC timestamp (milliseconds)

    """

    date = datetime.now(timezone.utc)

    return int(date.timestamp() * 1000)


def TimestampToDatetime(timestamp):
    """
    API requires UTC timestamp in milliseconds for the end/{end}/ path variable

    Parameters
    ----------
    date : int
        timestamp

    Returns
    -------
    datetime
        datetime Object

    """

    return datetime.fromtimestamp(timestamp)
