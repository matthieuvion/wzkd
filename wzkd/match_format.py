import datetime
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from itertools import product
from labels import MODES_LABELS, WEAPONS_CAT_PREFIX, WEAPONS_CAT, CW_WEAPONS_CAT_SUFFIX, WEAPONS_CAT_LABELS, WEAPONS_LABELS



def MatchPlayersToDf(match):
    """
    Convert Match result to a DataFrame we we can perform our aggregations nicely, later.
    Expand some entries (i.e player, playerstats) that are deeply nested.
    Filter out / retains columns.
    Built mainly to analyze a 'BR' match, but we made sure it should work for other match types
    
    Parameters
    ----------
    match : result from COD API "match" endpoint ; FYI formated as : 
        list[
                dict{ player 1 match stats },
                dict{ player 2 match stats },
                dict{ +- 150 players },
            ]
    
    Returns
    -------
    DataFrame, a match stats with players as rows, matches/player stats as columns/values
    """
    
    
    keep_cols =  [
        'mode',
        'utcEndSeconds',
        'team',
        'username',
        'timePlayed',
        'teamPlacement',
        'kdRatio', 
        'kills', 
        'deaths', 
        'assists', 
        'damageDone',
        'damageTaken',
        'gulagKills',
        'percentTimeMoving',
        'duration'
        ]
    
    df = pd.DataFrame(match)
    
    # column playerStats is a series of dict, we can expand it easily and append, then drop the original
    df = pd.concat([df.drop(['playerStats'], axis=1), df['playerStats'].apply(pd.Series)], axis=1)
    
    # colum 'player' has more depth
    # once expanded, it has a column 'loadout' : a series of list of dict (either one or more, we will max 3)
    # and also brMissionStats (mostly empty ?, a col only present in BR matches) that we aren't interested in
    
    df = pd.concat([df.drop(['player'], axis=1), df['player'].apply(pd.Series)], axis=1)
    if 'brMissionStats' in df.columns:
        df = df.drop(['brMissionStats'], axis = 1)
    df = pd.concat([df.drop(['loadout'], axis=1), df['loadout'].apply(pd.Series)], axis=1)
    for col in range(0,3):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x['primaryWeapon']['name']} - {x['secondaryWeapon']['name']}" if not str(x) == 'nan' else np.nan)
            col_name = "loadout_" + str(col +1)
            df = df.rename(columns={col: f"loadout_{str(col +1)}"})   
            keep_cols.append(col_name)
    
    # Ensure we are not throwing an error if we want to keep a column that does not exist (i.e. not in a BR match) :
    keep_cols = [col for col in keep_cols if col in df.columns.tolist()]
    
    return df[keep_cols]
    
    
def MatchPlayersStandardize(df):
    """
    A first layer of standadization (as properly formated) to our a "Match with players stats" DataFrame
    For further aggregations / better readibility of our data
    
    Returns
    -------
    DataFrame : players/teams as rows, cleaned player stats of a given match as columns
    """
    
    int_cols =  [
        'teamPlacement', 
        'kills', 
        'deaths', 
        'assists', 
        'gulagKills', 
        'damageDone',
        'damageTaken'
        ]
    
    float_cols = [
        'kdRatio',
        'percentTimeMoving'
        ]
    
    ts_cols = [
        'utcEndSeconds'
        ]
    
    columns_labels = {
        'utcEndSeconds':'Ended at',
        'timePlayed': 'Playtime',
        'teamPlacement':'#',
        'kdRatio':'KD',
        'damageDone':'Damage >',
        'damageTaken':'Damage <',
        'gulagKills':'Gulag',
        'headshots':'% headshots',
        'percentTimeMoving':'% moving',
        'duration':'Game duration'
        }

    # Ensure we are not throwing an error if we want to keep a column that does not exist (i.e. not in a BR match) :
    int_cols = [col for col in int_cols if col in df.columns.tolist()]
    
    # df = df.fillna(0)
    # generic conversions/rounding for int and float cols
    df[int_cols] = df[int_cols].astype(int)
    df[float_cols] = df[float_cols].astype(float).round(1) # still renders 0.0000 in streamlit but ugly hacks exists
    
    # specials : timestamp, loadout columns, match type...
    df.team = df.team.apply(lambda x: x.replace("team_", ""))
    df['utcEndSeconds'] = df['utcEndSeconds'].apply(lambda x: datetime.fromtimestamp(x))
    
    df['duration'] = df['duration'].apply(lambda x: x/1000).apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M')) # API duration is in seconds x1000
    df['timePlayed'] = df['timePlayed'].apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M:%S')) # API timePlayed is in seconds
    if 'gulagKills' in df.columns.tolist():
        df['gulagKills'] = df['gulagKills'].map({1:'W', 0:'L'})
    for col in ['loadout_1', 'loadout_2', 'loadout_3']:
            df.fillna({col:'-'}, inplace=True) if col in df.columns else None
    
    df = df.replace({"mode": MODES_LABELS})
    df = df.rename(columns=columns_labels)
    df.columns = df.columns.str.capitalize()
    df = df.rename({"Kd":"KD"}, axis=1)
     
    return df

def retrieveTeam(df, gamertag):
    """ --> str, Retrieve team name of given gamertag"""    
    return df[df["Username"] == gamertag]['Team'].tolist()[0]  


def retrieveTeammates(df, gamertag):
    """ --> list(str), Retrieve list of gamertag + his teammates"""  
    team = retrieveTeam(df, gamertag)
    return df[df["Team"] == team]['Username'].tolist()


def retrieveDate(df):
    """ --> str, Retrieve end date (str) of our match """   
    return df['Ended at'][0].strftime('%Y-%m-%d %H:%M')

def retrieveMode(df):
    """ --> str, retrieve BR type of our match """
    return df['Mode'][0]

def retrievePlacement(df, gamertag):
    """ --> int, Retrieve final placement of a player/his team """  
    return df[df["Username"] == gamertag]["#"].tolist()[0]

def retrievePlayerKills(df, gamertag):
    """ --> dict, Retrieve given Player KD, Kills, Deaths"""
    return df[df["Username"] == gamertag][["KD", "Kills", "Deaths"]].to_dict('records')[0]

def convertWeapons(x):
    """ Clean Loadouts (weapons) columns, particul. using labels.py """
    
    # Cold War weapons format is iw8_sm_t9, iw8_ar_t9 etc. for Cold War,  Modern Warfare : iw8_ar, iw8_me etc. for MW
    if not x == "-":
        x = x.split(" - ")
        x = list(map(lambda weapon: weapon.replace(WEAPONS_CAT_PREFIX[0], ''), x))
        x = list(map(lambda weapon: WEAPONS_LABELS.get(weapon) or weapon, x))
        
        # After a won Gulag you (usually) spawn with 'fists' and season weapon (usually Pistols); remove 'fists'
        if 'fists' in x:
            x = list(map(lambda weapon: weapon.replace('fists', ''), x))
            x = x[0]
        else:
            x = ' - '.join(x)
    else:
        x = '-'
    return x


def teamKills(df, gamertag):
    """ Return a DataFrame with Team players KD, K/D/A; also with agg stats for whole Team """
    team = retrieveTeam(df, gamertag)
    df_team = df[df["Team"] == team][['Username', 'KD', 'Kills', 'Deaths', 'Assists']]
    agg_func = {
        "KD":"sum",
        "Kills":"sum",
        "Deaths":"sum",
        "Assists":"sum"
    }
    team_kd = (df_team.Kills.sum() / df_team.Deaths.sum()).round(1)

    row_total = df_team.agg(agg_func).to_dict()
    row_total.update({'Username': 'Team'})
    row_total.update({'KD': team_kd})
    df_team = df_team.append(row_total, ignore_index=True)
    df_team[['Kills', 'Deaths', 'Assists']] = df_team[['Kills', 'Deaths', 'Assists']].astype(int)
    return df_team

def teamWeapons(df, gamertag):
    """ Return a DataFrame with teammates and their loadouts (3 max) """
    team = retrieveTeam(df, gamertag)
    df_weapons = df[df["Team"] == team][df.columns[df.columns.str.startswith('Loadout')]]
    df_usernames = df[df["Team"] == team][['Username']]
    table_weapons = pd.concat([df_usernames, df_weapons], axis=1)
    for col in table_weapons.columns[table_weapons.columns.str.startswith('Loadout')]:
        table_weapons[col] = table_weapons[col].map(lambda x: convertWeapons(x))
    return table_weapons

def teamPercentageKills(df,gamertag):
    team = retrieveTeam(df, gamertag)
    tkills = df[df["Team"] == team].Kills.sum()
    gkills = df.Kills.sum()
    return ((tkills * 100) / gkills).round(1)

def teamKillsPlacement(df, gamertag):
    """ Retrieve final placement according to # kills, of a player/his team """ 
    index = df.groupby('Team')[['Kills']].sum().sort_values('Kills', ascending = False).reset_index()
    condition = index['Team'] == retrieveTeam(df, gamertag)
    return index[condition]['Kills'].index.tolist()[0]

def topPlayers(df):
    """  """
    df_top = df.sort_values(by=["Kills", 'KD'],ascending=False)[0:5][
        ['Username', 'Team', 'KD', 'Kills', 'Deaths', 'Assists', 'Loadout_1', 'Loadout_2', 'Loadout_3']
        ]

    for col in df_top.columns[df_top.columns.str.startswith('Loadout')]:
        df_top[col] = df_top[col].map(lambda x: convertWeapons(x))
    return df_top

def playersQuartiles(df):
    """ --> dict, All players quartiles (+ mean) that match for Kills and KD """
    return df[['Kills', 'KD']].describe().to_dict()