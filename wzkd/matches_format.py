import datetime
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from labels import mode_labels


def getLastMatchId(matches):
    """ Extract last (Battle Royale) Match ID from last matches """
    list_br_match = [match for match in matches if "br_br" in match["mode"]]
    last_match_id = int(list_br_match[0]["matchID"]) if len(list_br_match) > 0 else None
    return last_match_id


def MatchesToDf(matches):
    """
    COD API / callofduty.py client --> list of dict : max 20 Matches with Player stats
    We expand Player and PlayerStats levels, concatenate them
    ! We drop some cols we dont want to work with

    Returns
    -------
    DataFrame, matches as rows, matches/ one player stats as columns
    """
    
    
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

#st.cache
def MatchesStandardize(df):
    """
    A first layer of standadization (as : properly formated) to our matches DataFrame
    For further aggregations / better readibility of our data
    
    Returns
    -------
    DataFrame : matches as rows, cleaned matches/player stats as columns
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
        'utcStartSeconds',
        'utcEndSeconds'
        ]
    
    columns_labels = {
        'utcEndSeconds':'Ended at',
        'utcStartSeconds':'Started at',
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

    df = df.fillna(0) # sometimes (Plunder only ?) rank, gulag is NaN
    df[int_cols] = df[int_cols].astype(int)
    df[float_cols] = df[float_cols].astype(float).round(1) # still renders 0.0000 in streamlit but ugly hacks exists
    
    # specials
    df['utcEndSeconds'] = df['utcEndSeconds'].apply(lambda x: datetime.fromtimestamp(x))
    df['utcStartSeconds'] = df['utcStartSeconds'].apply(lambda x: datetime.fromtimestamp(x))
    
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
     
#st.cache
def MatchesPerDay(df):
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
    
    drop_cols =  [
        'Started at',
        'Playtime',
        '% moving',
        'Game duration'
        ]
    
    keep_cols = [
        'End time',
        'Mode',
        '#',
        'KD',
        'Kills',
        'Deaths',
        'Assists',
        'Damage >',
        'Damage <',
        'Gulag'
    ]
    
    loadout_cols = df.columns[df.columns.str.startswith('Loadout')].tolist()
    df[loadout_cols] = df[loadout_cols].replace(0, '-') # else can't concat Loadouts cols
    
    # 1. --- initial formating : datetime, concat loadouts cols ---
    
    df = df.drop(drop_cols, axis = 1)
    df['End time'] = df['Ended at'].dt.time
    
    def concat_loadouts(df, columns):
        return pd.Series(map(' , '.join, df[columns].values.tolist()),index = df.index)
    
    df['Weapons'] = concat_loadouts(df, loadout_cols)
    keep_cols = [*keep_cols, *['Weapons']]
    
    # 2. --- build result {"day1": df-matches-that-day, "day2": df...} ---
    
    list_df = [g for n, g in df.groupby(pd.Grouper(key='Ended at',freq='D'))]
    list_df = [df for df in list_df if not df.empty]
    list_days = [df['Ended at'].tolist()[0].strftime('%A') for df in list_df]
    
    # make sure we display latest day first, then build dictionary
    for list_ in [list_days, list_df]:
        list_.reverse()
    day_matches = dict(zip(list_days, list_df))
    
    # 3. --- some more (re)formating ---
    
    # for some reason (me ? ^-^, Grouper => Series?) couldnt' modify df before building the result, must iterate again 
    for k, v in day_matches.items():
        day_matches[k] = day_matches[k][keep_cols]
      
    return day_matches


def AggStats(df):
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

    agg_func = {
        "Mode":"count",
        "Kills":"sum",
        "Deaths":"sum"
    } 
    dict_ = df.agg(agg_func).to_dict()
    dict_.update({'KD': (df.Kills.sum() / df.Deaths.sum()).round(2)})
    dict_.update({'Gulags': int((df.Gulag.str.count("W").sum() / df.Gulag.str.count("L").sum())*100)})
    dict_['Played'] = dict_.pop('Mode')
    
    
    return dict_