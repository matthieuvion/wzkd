import datetime
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from labels import mode_labels




def MatchPlayersToDf(match):
    """
    COD API / callofduty.py client --> list of dict : +- 150 players with their stats in a given match
    Share similar strucure (keys) to Matches result, thus very similar operations to what's performed in MatchesToDf()
    We expand Player and PlayerStats levels, concatenate them
    ! We drop some cols we dont want to work with; while having 2 new cols 'team' and 'username' (compared to Matches result)
    
    Returns
    -------
    DataFrame, a match stats, players as rows, matches/player stats as columns
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
    
    # colum player has more depth
    # once expanded, it has a column 'loadout' : a series of list of dict (either one or more, we will keep 1 to max 3)
    # and also brMissionStats (mostly empty ?) that we aren't interested in
    
    df = pd.concat([df.drop(['player'], axis=1), df['player'].apply(pd.Series)], axis=1)
    df = df.drop(['brMissionStats'], axis = 1)
    df = pd.concat([df.drop(['loadout'], axis=1), df['loadout'].apply(pd.Series)], axis=1)
    for col in range(0,3):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x['primaryWeapon']['name']} - {x['secondaryWeapon']['name']}" if not str(x) == 'nan' else np.nan)
            col_name = "loadout_" + str(col +1)
            df = df.rename(columns={col: f"loadout_{str(col +1)}"})   
            keep_cols.append(col_name)
    
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

    # df = df.fillna(0)
    df[int_cols] = df[int_cols].astype(int)
    df[float_cols] = df[float_cols].astype(float).round(1) # still renders 0.0000 in streamlit but ugly hacks exists
    
    # specials
    df['utcEndSeconds'] = df['utcEndSeconds'].apply(lambda x: datetime.fromtimestamp(x))
    
    df['duration'] = df['duration'].apply(lambda x: x/1000).apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M')) # API duration is in seconds x1000
    df['timePlayed'] = df['timePlayed'].apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M:%S')) # API timePlayed is in seconds
    df['gulagKills'] = df['gulagKills'].map({1:'W', 0:'L'})
    for col in ['loadout_1', 'loadout_2', 'loadout_3']:
            df.fillna({col:'-'}, inplace=True) if col in df.columns else None
    
    df = df.replace({"mode": mode_labels})
    df = df.rename(columns=columns_labels)
    df.columns = df.columns.str.capitalize()
    df = df.rename({"Kd":"KD"}, axis=1)
     
    return df