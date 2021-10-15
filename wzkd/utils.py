import datetime
from datetime import datetime, timezone
import pandas as pd
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

st.cache
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
    # col playerStats is a series of dict
    df = pd.concat([df.drop(['playerStats'], axis=1), df['playerStats'].apply(pd.Series)], axis=1)
    df = df[keep_cols]
    
    return df

st.cache
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
        'br_dmz_plunquad':'Pldr x4'

        }
    
    columns_labels = {
        'mode':'Mode',
        'utcEndSeconds':'Ended at',
        'utcStartSeconds':'Started at',
        'timePlayed': 'Playtime',
        'teamPlacement':'Placement',
        'kdRatio':'KD',
        'kills':'Kills',
        'deaths':'Deaths',
        'assists':'Assists',
        'damageDone':'Damage ->',
        'damageTaken':'<- Damage',
        'gulagKills':'Gulag',
        'headshots':' % headshots',
        'percentTimeMoving':'% moving',
        'duration':'Game duration'
        }

    df = df.fillna(0)
    df[int_cols] = df[int_cols].astype(int)
    df[float_cols] = df[float_cols].astype(float).round(1) # still renders 0.0000 in streamlit but ugly hack exists
    for col in ts_cols:
        df[col] = df[col].apply(pd.to_datetime, unit='s')
    
    #  specials
    df['duration'] = df['duration'].apply(lambda x: x/1000).apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M:%S')) # duration is in seconds x1000
    df['timePlayed'] = df['timePlayed'].apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M:%S')) # timePlayed is in seconds
    df['gulagKills'] = df['gulagKills'].map({1:'W', 0:'L'})
    
    # final naming
    df = df.replace({"mode": mode_labels})
    df = df.rename(columns=columns_labels)
    
    return df

st.cache
def MatchesPerDay(df):
    
    drop_cols =  [
        'Started at',
        'Playtime',
        '% moving',
        'Game duration'
        ]
    df = df.drop(drop_cols, axis = 1)
    df['End time'] = df['Ended at'].dt.time
    
    # group by day --> several dataframes, get weekday and output a dict
    df_days = [g for n, g in df.groupby(pd.Grouper(key='Ended at',freq='D'))]
    string_days = [df['Ended at'].tolist()[0].strftime('%A') for df in df_days]
    dict_dfs = dict(zip(string_days, df_days))

    # for some reason (me ? ^-^, Grouper ?) cannot edit-save df before, must iterate again
    for key, value in dict_dfs.items():
        dict_dfs[key] = dict_dfs[key].drop(['Ended at'], axis=1)
        dict_dfs[key] = dict_dfs[key][['End time', 'Mode', 'Placement', 'KD', 'Kills', 'Deaths', 'Assists', 'Damage ->', '<- Damage', 'Gulag']]
        
    return dict_dfs
# summary2 = await player.matchesSummary(Title.ModernWarfare, Mode.Warzone, end= utc_timestamp, limit=15)