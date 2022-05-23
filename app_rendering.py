import streamlit as st
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder

from src import utils


""" 
Inside
------
Functions to render our Data nicely in Streamlit
After many tests, we found out that best results (to us) would be :
- rendering dataframes mainly as Ag Grid tables, using Streamlit Ag Grid component
- rendering charts with plotly
- while still applying some hacks/tricks to better display our --previously, dataframes
- aka : no use of multi indexes df that would render with blank rows, convert dtype datetime, tighten up our tables etc...
"""


# maybe later, could be rendered as a timeline
# https://discuss.streamlit.io/t/reusable-timeline-component-with-demo-for-history-of-nlp/9639
def render_session(df_session, CONF):
    """Rendering layer to matches history (several session tables)

    Streamlit or even AgGrid does not render well dfs with a multi index, aka : blank rows etc.)
    We structure and display our data differently : one df => dfs grouped by session + print of sessions aggregated stats
    Maybe later with some cell highlights cf. https://discuss.streamlit.io/t/ag-grid-component-with-input-support/8108/184
    """

    # tighter our data(frame)
    df_session["K D A"] = utils.concat_cols(
        df_session, to_concat=["kills", "deaths", "assists"], sep=" | "
    )

    # customize table layout (streamlit ag grid component)
    df_session = df_session.rename(columns=CONF.get("APP_DISPLAY").get("labels"))
    visible_cols = [
        "Ended at",
        "mode",
        "#",
        "KD",
        "K D A",
        "Gulag",
    ]

    gb = GridOptionsBuilder.from_dataframe(df_session[visible_cols])
    gb.configure_column(
        "KD",
        type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
        precision=2,
    )
    gb.configure_column(
        "Ended at", type=["customDateTimeFormat"], custom_format_string="HH:mm"
    )
    height = len(df_session) * 30 + 40
    table = AgGrid(
        df_session[visible_cols],
        gridOptions=gb.build(),
        height=height,  # hard coded height, works well for default aggrid theme
        fit_columns_on_grid_load=False,
    )


# gb.configure_column("date_tz_aware", type=["dateColumnFilter","customDateTimeFormat"], custom_format_string='yyyy-MM-dd HH:mm zzz', pivot=True)


def render_session_stats(dict_):
    """Rendering layer to aggregated stats of matches history (multiple sessions tables)"""
    # NewLine can't be (or couldn't find a working hack), must do multiple prints

    st.caption(
        f"<div style='text-align: right;'>{dict_['utcEndSeconds'].strftime('%m.%d.%y')} </div>",
        unsafe_allow_html=True,
    )

    st.caption(
        f"<div style='text-align: right;'>{dict_['played']} matches : {dict_['kdRatio']:.2f} k/d </div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"<div style='text-align: right;'>{round(dict_['kills']/dict_['played'], 2)} k. avg | {dict_['gulagStatus']:.0%} g. win </div>",
        unsafe_allow_html=True,
    )


def render_last_session(last_stats, CONF):
    """Rendering layer to last session, as a table"""

    # tighter our data(frame)
    last_stats["K D A"] = utils.concat_cols(
        last_stats, to_concat=["kills", "deaths", "assists"], sep=" | "
    )
    last_stats["Damage avg"] = utils.concat_cols(
        last_stats, to_concat=["damageDone", "damageTaken"], sep=" | "
    )

    # customize table layout (streamlit ag grid component)
    last_stats = last_stats.rename(columns=CONF.get("APP_DISPLAY").get("labels"))
    visible_cols = [
        "Player(s)",
        "Matches",
        "KD",
        "K D A",
        "Damage avg",
        "Gulag",
    ]

    gb = GridOptionsBuilder.from_dataframe(last_stats[visible_cols])
    gb.configure_column(
        "KD",
        type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
        precision=2,
    )
    # gb.configure_column(
    #    "Gulag",
    #    type=["customNumericFormat"],
    #    precision=2,
    # )

    height = len(last_stats) * 30 + 40
    table = AgGrid(
        last_stats[visible_cols],
        gridOptions=gb.build(),
        height=height,  # hard coded height, works well for default aggrid theme
        fit_columns_on_grid_load=False,
    )


def render_team(team_kills, gamertag):
    """Render Team KDA concat with Team Weapons, in a plotly table"""

    team_kills = utils.shrink_df(
        team_kills,
        cols_to_concat=["Kills", "Deaths", "Assists"],
        str_join=" | ",
        new_col="K D A",
    )
    cols_to_concat = team_kills.columns[
        team_kills.columns.str.startswith("Loadout")
    ].tolist()
    team_kills = utils.shrink_df(
        team_kills, cols_to_concat, str_join=", ", new_col="Loadouts"
    )

    # team_info = pd.concat([team_kills, team_weapons], axis=1, sort=True)
    team_info = team_kills.rename(columns={"Username": "Player"})
    team_info["Loadouts"] = team_info["Loadouts"].map(lambda x: utils.remove_empty(x))

    # plot with plotly
    colors = [
        "#F9B400" if player == gamertag else "white"
        for player in team_info["Player"].tolist()
    ]
    colors[-1] = "lightgrey"

    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[30, 15, 20, 60],
                header=dict(
                    values=list(team_info.columns),
                    align=["left"],
                    line_color="#F0F2F6",
                    fill_color="white",
                ),
                cells=dict(
                    values=[
                        team_info.Player,
                        team_info.KD,
                        team_info["K D A"],
                        team_info.Loadouts,
                    ],
                    align="left",
                    fill_color=[colors],
                    font_size=13,
                ),
            )
        ]
    )

    # to narrow spaces between several figures
    fig.update_layout(width=600, height=150, margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)
    # st.dataframe(team_info)
    # hack remove index, but keep empty col still : st.dataframe(team_info.assign(hack='').set_index('hack'))


def render_players(players_kills):
    """Render Game top Kills players in a plotly table"""

    players_kills = utils.shrink_df(
        players_kills,
        cols_to_concat=["Kills", "Deaths", "Assists"],
        str_join=" | ",
        new_col="K D A",
    )
    cols_to_concat = players_kills.columns[
        players_kills.columns.str.startswith("Loadout")
    ].tolist()
    players_kills = utils.shrink_df(
        players_kills, cols_to_concat, str_join=", ", new_col="Loadouts"
    )

    players_kills = players_kills.rename(columns={"Username": "Player"})
    players_kills["Loadouts"] = players_kills["Loadouts"].map(
        lambda x: utils.remove_empty(x)
    )

    # plot with plotly
    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[30, 20, 15, 20, 60],
                header=dict(
                    values=list(players_kills.columns),
                    align=["left"],
                    line_color="#F0F2F6",
                    fill_color="white",
                ),
                cells=dict(
                    values=[
                        players_kills.Player,
                        players_kills.Team,
                        players_kills.KD,
                        players_kills["K D A"],
                        players_kills.Loadouts,
                    ],
                    align="left",
                    fill_color="white",
                    font_size=13,
                ),
            )
        ]
    )

    # to narrow spaces between several figures
    fig.update_layout(width=600, height=250, margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)


def render_bullet_chart(
    lifetime_kd, lifetime_kills_ratio, player_kills, players_quartiles
):
    """Renders Players' Kills and KD in a plotly bullet chart : performance this match vs. lifetime, and all players quartiles"""

    # match values
    # readify some variables (from Profile & Match stats) to make our comparisons more explicit
    kd_player = player_kills["KD"] if not player_kills["KD"] == 0 else 0.1
    kd_mean = round(players_quartiles["KD"]["mean"], 1)
    kd_median = round(players_quartiles["KD"]["50%"], 1)
    kd_Q3 = round(players_quartiles["KD"]["75%"], 1)
    kd_max = round(players_quartiles["KD"]["max"], 1)

    kills_player = player_kills["Kills"] if not player_kills["KD"] == 0 else 0.1
    kills_mean = round(players_quartiles["Kills"]["mean"], 1)
    kills_median = round(players_quartiles["Kills"]["50%"], 1)
    kills_Q3 = round(players_quartiles["Kills"]["75%"], 1)
    kills_max = round(players_quartiles["Kills"]["max"], 1)

    len_gauge_kd = 2
    len_gauge_kills = 6
    fig = go.Figure()

    # plot kd bullet chart
    ticks = [kd_median, kd_mean, kd_Q3, len_gauge_kd]

    fig.add_trace(
        go.Indicator(
            mode="number+gauge+delta",
            value=kd_player,
            domain={"x": [0.1, 1], "y": [0.8, 1]},
            title={"text": "K/D", "font_size": 15},
            delta={"reference": lifetime_kd},
            gauge={
                "shape": "bullet",
                "axis": {
                    "range": [None, len_gauge_kd],
                    "tickmode": "array",
                    "tickvals": ticks,
                    "ticktext": [
                        f"...{int(kd_max)}" if i == len_gauge_kd else i for i in ticks
                    ],
                },
                "threshold": {
                    "line": {"color": "black", "width": 2},
                    "thickness": 0.75,
                    "value": lifetime_kd,
                },
                "steps": [
                    {"range": [0, kd_median], "color": "grey"},
                    {"range": [kd_median, kd_mean], "color": "darkgrey"},
                    {"range": [kd_mean, kd_Q3], "color": "lightgrey"},
                ],
                "bar": {"color": "black"},
            },
        )
    )

    # plot kills bullet chart
    ticks = [kills_median, kills_mean, kills_Q3, len_gauge_kills]

    fig.add_trace(
        go.Indicator(
            mode="number+gauge+delta",
            value=kills_player,
            domain={"x": [0.1, 1], "y": [0.4, 0.6]},
            title={"text": "Kills", "font_size": 15},
            delta={"reference": lifetime_kills_ratio},
            gauge={
                "shape": "bullet",
                "axis": {
                    "range": [None, len_gauge_kills],
                    "tickmode": "array",
                    "tickvals": ticks,
                    "ticktext": [
                        f"...{int(kills_max)}" if i == len_gauge_kills else i
                        for i in ticks
                    ],
                },
                "threshold": {
                    "line": {"color": "black", "width": 2},
                    "thickness": 0.75,
                    "value": lifetime_kills_ratio,
                },
                "steps": [
                    {"range": [0, kills_median], "color": "grey"},
                    {"range": [kills_median, kills_mean], "color": "darkgrey"},
                    {"range": [kills_mean, kills_Q3], "color": "lightgrey"},
                ],
                "bar": {"color": "black"},
            },
        )
    )

    fig.update_layout(height=180, width=600, margin={"t": 0, "b": 0, "l": 15, "r": 0})
    st.plotly_chart(fig, use_container_width=False)
