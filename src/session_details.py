import itertools


def get_session_teammates(last_session, gamertag):
    """Get list of teammates from your last session of BR matches"""
    ids = last_session.query("username == @gamertag")["matchID"].tolist()
    teams = last_session.query("username == @gamertag")["team"].tolist()
    teammates = []
    for id_, team in zip(ids, teams):
        teammates.extend(
            last_session.query("matchID == @id_ & team == @team")["username"].tolist()
        )

    return list(set(teammates))


def stats_last_session(last_session, teammates):
    """last session > n battle royale matches > formatted > agregated stats"""

    aggregations = {
        "mode": "count",
        "kills": "sum",
        "deaths": "sum",
        "assists": "sum",
        "damageDone": "mean",
        "damageTaken": "mean",
        "gulagStatus": lambda x: (x.eq("W").sum() / x.isin(["W", "L"]).sum())
        if x.eq("W").sum() > 0
        else 0,
    }

    agg_session = (
        last_session.query("username in @teammates")
        .groupby("username")
        .agg(aggregations)
        .rename(columns={"mode": "played"})
        .reset_index()
    )
    agg_session["kdRatio"] = agg_session.kills / agg_session.deaths

    def gulag_format(gulag_value):
        return str(int(gulag_value * 100)) + " %"

    agg_session.gulagStatus = agg_session.gulagStatus.apply(gulag_format)

    return agg_session
