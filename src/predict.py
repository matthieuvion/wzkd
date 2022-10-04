from typing import List, Dict

import pandas as pd
import numpy as np
import datetime
from datetime import datetime
import pickle

import streamlit as st


from sklearn.preprocessing import OneHotEncoder
import xgboost as xgb

""" 
Inside
------
Pipeline for shaping /creating  features to predict avg lobby kill/death ratio (aka "lobby kd") for Resurgence matches
For now, model only works for Resurgence modes (regular Solos to Quads), on maps Rebirth Island and Fortune Keep

Predicted lobby kd is meant to be similar to what wzranked.com computes with a good access to COD API,
(notably players seasonal average k/d ratio, with a lot of calls made to the API and a database to store data)

Notes on "lobby kd" & observed variance : 
- "lobby kd" calculated as : average [players' kills/deaths )
- Usually wzranked computes it from 50 to 90 % known player seasonal (resurgence) k/d, so 'true' lobby kd varies
- Our model has a mean rmse of += [0.09 - 0.1] ; FYI "lobby k/d" usually navigates between 0.6 (rare) and 1.5 (rare)
"""


def to_model_format(last_session: List[Dict]):
    """
    Convert our last matches to what our training dataset looked like
    """

    df = pd.json_normalize(last_session)

    def parse_squad(x):
        """Extract squad size from column 'mode'"""
        if "quad" in x:
            y = "Quads"
        elif "trios" in x:
            y = "Trios"
        elif "duos" in x:
            y = "Duos"
        elif "solo" in x:
            y = "Solos"
        elif "solos" in x:
            y = "Solos"
        else:
            y = "Solos"
        return y

    def parse_map(x):
        """Extract map type from column 'mode'"""
        if "rbrth" in x:
            y = "rebirth"
        else:
            y = "fortkeep"
        return y

    df["squad"] = df["mode"].apply(parse_squad)
    df["map"] = df["mode"].apply(parse_map)

    categorical_features = ["map", "squad"]
    df[categorical_features] = df[categorical_features].astype("category")

    return df


def select_features(df):
    """
    Retains the best columns to features to be built upon
    """
    to_keep = [
        "matchID",
        "utcEndSeconds",
        "map",
        "squad",
        "duration",
        "playerCount",
        "teamCount",
        "playerStats.kills",
        "playerStats.deaths",
        "playerStats.assists",
        "playerStats.scorePerMinute",
        "playerStats.headshots",
        "playerStats.rank",
        "playerStats.distanceTraveled",
        "playerStats.teamSurvivalTime",
        "playerStats.kdRatio",
        "playerStats.timePlayed",
        "playerStats.percentTimeMoving",
        "playerStats.damageDone",
        "playerStats.damageTaken",
        "player.awards.streak_5",
        "player.awards.double",
        "player.brMissionStats.missionsComplete",
    ]

    return df[to_keep]


def encode_features(df):
    """
    Encode datetime, categorical (squad size, map type) columns
    """

    def encode_datetime(df):
        """
        Add day of week, hour, from timestamp
        """

        df["utcEndSeconds"] = df["utcEndSeconds"].apply(
            lambda x: datetime.fromtimestamp(x)
        )
        df["weekday"] = df["utcEndSeconds"].dt.weekday
        df["hour"] = df["utcEndSeconds"].dt.hour
        # df.drop("utcEndSeconds", axis=1, inplace=True)

        return df

    def squad_to_ordinal(df):
        """
        label (ordinal) encoding for 'squad' (Solos, Duos, Trios...)
        (could also use one hot, but squad is kind of ordinal)
        """
        squad_order = {"Solos": 1, "Duos": 2, "Trios": 3, "Quads": 4}
        df["squad_ordinal"] = df["squad"].map(squad_order)
        df["squad_ordinal"] = df["squad_ordinal"].astype("int64")
        df.drop("squad", axis=1, inplace=True)

        return df

    def one_hot(df, column: str):
        """
        One Hot Encode one categorical column using sklearn
        ohe encoder previously fit when we built our model
        """

        with open("src/model/ohe_encoder.pickle", "rb") as f:
            enc = pickle.load(f)
        encoded_features = enc.transform(df[[column]]).toarray()

        df_features = pd.DataFrame(encoded_features)
        columns = enc.get_feature_names_out([column]).tolist()
        df_features.columns = columns

        for _ in [df, df_features]:
            _.reset_index(drop=True, inplace=True)
        augmented_df = pd.concat([df, df_features], axis=1)
        augmented_df.drop(column, axis=1, inplace=True)

        return augmented_df

    # apply encoding
    encoded_df = encode_datetime(df)
    encoded_df = squad_to_ordinal(encoded_df)
    encoded_df = one_hot(encoded_df, column="map")

    return encoded_df


def create_new_features(df):
    """
    Create new features from existing features
    We calculated and tried a lot, but found those ones to work better
    """

    def add_time_slot(df):
        """
        Hour (0-24) had not much effect, let's custom-bin it
        morning (1), noon (2), afternoon (3), evening (4), late evening (5)
        """
        dict_ = {
            6: 1,
            7: 1,
            8: 1,
            9: 1,
            10: 1,
            11: 2,
            12: 2,
            13: 2,
            14: 3,
            15: 3,
            16: 3,
            17: 3,
            18: 4,
            19: 4,
            20: 4,
            21: 4,
            22: 5,
            23: 5,
            0: 5,
            1: 5,
            2: 5,
            3: 5,
            4: 5,
            5: 5,
        }
        df["time_slot"] = df["hour"].map(dict_)

        return df

    def normalize_by_time_played(df):
        """
        kills, damage... / time played
        """
        columns = [
            "playerStats.kills",
            "playerStats.deaths",
            "playerStats.damageDone",
            "playerStats.damageTaken",
        ]
        for col in columns:
            df[col + "_by_timePlayed"] = df[col].div(df["playerStats.timePlayed"])

        return df

    def damage_by_kill(df):
        """
        damageDone to get a kill
        """
        columns = [
            "playerStats.damageDone",
        ]
        for col in columns:
            df[col + "_by_kill"] = df[col].div(df["playerStats.kills"])

        return df

    def headshot_by_kill(df):
        """
        headshot / kill
        """
        columns = [
            "playerStats.headshots",
        ]
        for col in columns:
            # + .1 to prevent inf / nan values
            df[col + "_by_kill"] = df[col].add(0.1).div(df["playerStats.kills"] + 0.1)

        return df

    # apply features creation

    augmented_df = add_time_slot(df)
    augmented_df = normalize_by_time_played(augmented_df)
    augmented_df = damage_by_kill(augmented_df)
    augmented_df = headshot_by_kill(augmented_df)

    return augmented_df


def perform_aggregations(df):
    """
    A match consist of +- 40 players (rows); we have only one single given target : "lobby kd"
    We aggregate players rows, sometimes adding new features, to keep one single array of features per match
    We tried others methods to aggregate (players placement, percentiles etc), but they did not add as much.
    """

    # those features won't be aggregated, because they're the same for all players
    no_agg_columns = [
        "utcEndSeconds",
        "duration",
        "playerCount",
        "teamCount",
        "weekday",
        "hour",
        "squad_ordinal",
        "map_fortkeep",
        "map_rebirth",
        "time_slot",
    ]

    # Features such as kills, deaths etc.. + newly created features are aggregated using, mean, std, median
    detailed_agg_columns = [
        "playerStats.rank",
        "playerStats.kdRatio",
        "playerStats.kills",
        "playerStats.deaths",
        "playerStats.assists",
        "playerStats.damageDone",
        "playerStats.damageTaken",
        "playerStats.kills_by_timePlayed",
        "playerStats.deaths_by_timePlayed",
        "playerStats.damageDone_by_timePlayed",
        "playerStats.damageTaken_by_timePlayed",
        "playerStats.damageDone_by_kill",
        "playerStats.scorePerMinute",
        "playerStats.teamSurvivalTime",
        "playerStats.timePlayed",
        "playerStats.percentTimeMoving",
        "player.awards.streak_5",
        "player.awards.double",
        "playerStats.headshots",
        "player.brMissionStats.missionsComplete",
        "playerStats.headshots_by_kill",
    ]

    # keep core features (do not vary per players) :

    df_core = df.groupby("matchID")[no_agg_columns].agg("last")

    # perform mean, std, median groupby-agg on other features:

    df_detailed = df.groupby("matchID")[detailed_agg_columns].agg(
        ["mean", "std", "median"]
    )
    df_detailed.columns = ["_".join(x) for x in df_detailed.columns]

    # perform special aggregations (count of given variables among players of a match),
    # adding new features :

    pct_players_0_kills = (
        df[["matchID", "playerStats.kills"]]
        .groupby("matchID")[["playerStats.kills"]]
        .apply(lambda x: (x == 0).sum())
    )
    pct_players_0_kills.columns = ["pct_players_0_kills"]
    pct_players_5_kills = (
        df[["matchID", "playerStats.kills"]]
        .groupby("matchID")[["playerStats.kills"]]
        .apply(lambda x: (x >= 5).sum())
    )
    pct_players_5_kills.columns = ["pct_players_5_kills"]
    pct_players_10_kills = (
        df[["matchID", "playerStats.kills"]]
        .groupby("matchID")[["playerStats.kills"]]
        .apply(lambda x: (x >= 10).sum())
    )
    pct_players_10_kills.columns = ["pct_players_10_kills"]

    pct_players_with_streak_5 = (
        df[["matchID", "player.awards.streak_5"]]
        .groupby("matchID")[["player.awards.streak_5"]]
        .apply(lambda x: (x.notnull()).sum() / len(x) * 100)
    )
    pct_players_with_streak_5.columns = ["pct_players_with_streak_5"]

    pct_players_with_double = (
        df[["matchID", "player.awards.double"]]
        .groupby("matchID")[["player.awards.double"]]
        .apply(lambda x: (x.notnull()).sum() / len(x) * 100)
    )
    pct_players_with_double.columns = ["pct_players_with_double"]

    pct_players_with_headshots = (
        df[["matchID", "playerStats.headshots"]]
        .groupby("matchID")[["playerStats.headshots"]]
        .apply(lambda x: (x.notnull()).sum() / len(x) * 100)
    )
    pct_players_with_headshots.columns = ["pct_players_with_headshots"]

    # concatenate all columns (features), along matchID index
    df = pd.concat(
        [
            df_core,
            df_detailed,
            pct_players_0_kills,
            pct_players_5_kills,
            pct_players_10_kills,
            pct_players_with_streak_5,
            pct_players_with_double,
            pct_players_with_headshots,
        ],
        axis=1,
    ).reset_index()

    return df


@st.cache(show_spinner=False)
def pipeline_transform(last_session: List[Dict]):
    """
    Apply all above functions to get our data ready for prediction

    Returns:
    -------
    DataFrame,
    matchID | utcEndSeconds | feature 1 | feature2 2 ...
    """
    df = to_model_format(last_session)
    df = select_features(df)
    df = encode_features(df)
    df = create_new_features(df)
    df = perform_aggregations(df)

    df_indexes = df[["matchID", "utcEndSeconds"]]
    df_features = df.drop(["matchID", "utcEndSeconds"], axis=1)

    # return df_indexes, df_features
    return df


@st.cache
def predict_lobby_kd(df):
    """
    Apply XGBoost Model to predict average lobby kd, from match stats

    Returns:
    --------
    DataFrame,
    matchID | utcEndSeconds | Estim. Avg KD
    """

    df_indexes, df_features = df[["matchID", "utcEndSeconds"]], df.drop(
        ["matchID", "utcEndSeconds"], axis=1
    )
    # predict game(s) lobby kd
    model = xgb.XGBRegressor()
    model.load_model("src/model/xgb_model_lobby_kd_2.json")
    prediction = model.predict(df_features)  # array

    # append back predictions to matchID & utcEndSeconds
    df_with_kd = df_indexes.copy()
    df_with_kd.insert(2, "Lobby KD", prediction.tolist())

    return df_with_kd
