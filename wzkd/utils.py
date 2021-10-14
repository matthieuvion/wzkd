import datetime
from datetime import datetime, timezone
import pandas as pd

  
  
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

def MatchesToDf(matches):
    
    keep_cols =  [
        'mode',
        'utcStartSeconds',
        'utcEndSeconds',
        'teamPlacement',
        'kdRatio', 
        'kills', 
        'deaths', 
        'assists', 
        'damageDone',
        'damageTaken',
        'gulagDeaths',
        'duration'
        ]

    df = pd.DataFrame(matches)
    # col playerStats is a series of dict
    df = pd.concat([df.drop(['playerStats'], axis=1), df['playerStats'].apply(pd.Series)], axis=1)
    df = df[keep_cols]
    
    return df

def FormatMatches(df):

    int_cols =  [
        'teamPlacement', 
        'kills', 
        'deaths', 
        'assists', 
        'gulagDeaths', 
        'damageDone',
        'damageTaken'
        ]
    
    float_cols = [
        'kdRatio'
        ]
    
    ts_cols = [
        'utcStartSeconds',
        'utcEndSeconds'
        ]
    
    mode_labels = {
        'br_brtrios':'trios',
        'br_brduos':'duos',
        'br_brquads':'quads',
        'br_dmz_plunquad':'plunder 4'

        }
    
    columns_labels = {
        'mode':'Mode',
        'utcEndSeconds':'Ended at',
        'utcStartSeconds':'Started at',
        'teamPlacement':'Placement',
        'kdRatio':'KD',
        'kills':'Kills',
        'deaths':'Deaths',
        'assists':'Assists',
        'damageDone':'Damage ->',
        'damageTaken':'Damage <-',
        'gulagDeaths':'Gulag',
        'duration':'Game duration'
        }

    df = df.fillna(0)
    df[int_cols] = df[int_cols].apply(pd.to_numeric, downcast='integer', errors='ignore')
    df[float_cols] = df[float_cols].apply(pd.to_numeric, downcast='float', errors='ignore').apply(lambda x: round(x, 2)) # still renders 0.0000 in streamlit but hack exists
    df[ts_cols] = df[ts_cols].apply(pd.to_datetime, unit='s')
    df['duration'] = df['duration'].apply(lambda x: x/1000).apply(lambda x: pd.to_datetime(x, unit='s').strftime('%M:%S'))
    
    df = df.replace({"mode": mode_labels})
    df = df.rename(columns=columns_labels)
    return df

def ExtractLastMatch(df):
    df = _
    return df


# summary2 = await player.matchesSummary(Title.ModernWarfare, Mode.Warzone, end= utc_timestamp, limit=15)