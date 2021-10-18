import datetime
from datetime import datetime, timezone
import pandas as pd
import numpy as np

import streamlit as st

  
  
# Getting the current date

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
    
    return  int(date.timestamp() * 1000)

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
    
    return  datetime.fromtimestamp(timestamp)

#st.cache
def MatchesToDf(matches):
    
    keep_cols =  [
        'mode',
        'utcStartSeconds',
        'utcEndSeconds',
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

    df = pd.DataFrame(matches)
    
    # column playerStats is a series of dict, we can expand it easily and append, then drop the original
    df = pd.concat([df.drop(['playerStats'], axis=1), df['playerStats'].apply(pd.Series)], axis=1)
    
    # colum player is a bit messy
    # once expanded, it has a column 'loadout' : a series of list of dict (either one or two)
    # and also brMissionStats that we aren't interested in
    
    df = pd.concat([df.drop(['player'], axis=1), df['player'].apply(pd.Series)], axis=1)
    df = df.drop(['brMissionStats'], axis = 1)
    df = pd.concat([df.drop(['loadout'], axis=1), df['loadout'].apply(pd.Series)], axis=1)
    for col in range(0,3):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: [x['primaryWeapon']['name'],x['secondaryWeapon']['name']] if not str(x) == 'nan' else np.nan)
            col_name = "loadout_" + str(col +1)
            df = df.rename(columns={col: f"loadout_{str(col +1)}"})   
            keep_cols.append(col_name)
    
    return df[keep_cols]

#st.cache
def MatchesStandardize(df):
    

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
        'utcStartSeconds',
        'utcEndSeconds'
        ]
    
    mode_labels = {
        'br_brtrios':'Trios',
        'br_brduos':'Duos',
        'br_brquads':'Quads',
        'br_dbd_dbd':'Iron Trials',
        'br_dmz_plunquad':'Pldr x4',
        'br_rumble_clash':'Rumble'

        }
    
    columns_labels = {
        'utcEndSeconds':'Ended at',
        'utcStartSeconds':'Started at',
        'timePlayed': 'Playtime',
        'teamPlacement':'Placement',
        'kdRatio':'KD',
        'damageDone':'Damage >',
        'damageTaken':'Damage <',
        'gulagKills':'Gulag',
        'headshots':'% headshots',
        'percentTimeMoving':'% moving',
        'duration':'Game duration'
        }

    df = df.fillna(0)
    df[int_cols] = df[int_cols].astype(int)
    df[float_cols] = df[float_cols].astype(float).round(1) # still renders 0.0000 in streamlit but ugly hack exists
    for col in ts_cols:
        df[col] = df[col].apply(pd.to_datetime, unit='s')
    
    #  specials
    df['duration'] = df['duration'].apply(lambda x: x/1000).apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M')) # API duration is in seconds x1000
    df['timePlayed'] = df['timePlayed'].apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M:%S')) # API timePlayed is in seconds
    df['gulagKills'] = df['gulagKills'].map({1:'W', 0:'L'})
    
    # final naming
    df = df.replace({"mode": mode_labels})
    df = df.rename(columns=columns_labels)
    df.columns = df.columns.str.capitalize()
    df = df.rename({"Kd":"KD"}, axis=1) 
     
    return df
#st.cache
def MatchesPerDay(df):
    """
    Streamlit/basic AgGrid does not render well multi indexed df
    So we organize data differently, though more complex ^_^
    
    Returns
    -------
    {
        str_weekday_1: {
            "matches":df-of-matches-that-day,
            "kd":'',
            "played":'',
            "kills":'',
            "deaths":''
            },
         str_weekday_2: {
            ...
            }
        }

    """
    
    drop_cols =  [
        'Started at',
        'Playtime',
        '% moving',
        'Game duration'
        ]
    df = df.drop(drop_cols, axis = 1)
    df['End time'] = df['Ended at'].dt.time
    
    # get list of dataframes (matches), grouped per day (+ remove if one is empt --no match was played this particular weekday)
    list_df = [g for n, g in df.groupby(pd.Grouper(key='Ended at',freq='D'))]
    list_df = [df for df in list_df if not df.empty]
    
    # get the list of days [str, str, ...] by extracting first value of datetime column
    list_days = [df['Ended at'].tolist()[0].strftime('%A') for df in list_df]
    
    # get kd, n kills, n deaths, n matches for each day
    list_kills = [df['Kills'].sum() for df in list_df]
    list_deaths = [df['Deaths'].sum() for df in list_df]
    list_played = [len(df) for df in list_df]
    list_kds = [(df['Kills'].sum()/df['Deaths'].sum()).round(2) for df in list_df]
    list_gulags = [int(((df.Gulag.str.count("W").sum()/df.Gulag.str.count("L").sum()).round(2))*100) for df in list_df]
    

    for list_ in [list_df, list_days, list_kills, list_deaths, list_played, list_kds, list_gulags]:
        list_.reverse()

    # construct final result : {"day1: {"matches":df, "kd":'', "matches":'', "kills":'', "deaths":''}, day2: {...}}
    result = {}
    for day, df, played, kd, kills, deaths, gulags in zip(list_days, list_df, list_played, list_kds, list_kills, list_deaths, list_gulags):
        result[day] = {"matches":df, "played":played, "kd":kd, "kills":kills, "deaths":deaths, "gulags":gulags}    
    
    
    # naming & formating
    # for some reason (me ? ^-^, Grouper ?) couldnt' modify df before building the result, must iterate again
    for k, v in result.items():
        result[k]["matches"] = result[k]["matches"].drop(['Ended at'], axis=1)
        result[k]["matches"] = result[k]["matches"][['End time', 'Mode', 'Placement', 'KD', 'Kills', 'Deaths', 'Assists', 'Damage >', 'Damage <', 'Gulag']]
      
    return result