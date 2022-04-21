import datetime
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def ProfileGetKpis(result):
    """
    From COD API Profile endpoint json/dict, export some {key: player stats}

    Returns
    -------
    dict
    """
    return {
        'level': int(result['level']),
        'prestige': int(result['prestige']),
        'matches_count_all': int(result['lifetime']['all']['properties']['totalGamesPlayed']),
        'matches_count_br': int(result['lifetime']['mode']['br']['properties']['gamesPlayed']),
        'br_kills': int(result['lifetime']['mode']['br']['properties']['kills']),
        'br_kills_ratio': round(result['lifetime']['mode']['br']['properties']['kills'] / result['lifetime']['mode']['br']['properties']['gamesPlayed'],1),
        'br_kd':round(result['lifetime']['mode']['br']['properties']['kdRatio'],2),
        'competitive_ratio': int(round(result['lifetime']['mode']['br']['properties']['gamesPlayed']*100/result['lifetime']['all']['properties']['totalGamesPlayed'],0))
    }