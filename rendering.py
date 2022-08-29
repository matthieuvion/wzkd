import streamlit as st
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder

from src import utils


""" 
Inside
------
Functions to render our Data nicely in Streamlit
After many tests, we found out that best results would be :

+ Overall (personal xp) good practices
--------

- tabular data : avoid multi indexes df that would render with blank rows in App (st or ag grid)
- convert dtype datetime so they look prettier
- tighten up columns/tables as much as possible to better fit in app layout
- In the App itself, max use of layout elements : container, st.columns etc.

+ Render librairies
--------

- tabular data w/ Ag Grid : if you want advanced filters/interactivity or,
- tabular data w/ Plotly tables : easier to use (e.g highlight cells) and fit nicer in layout (custom width)
- rendering charts with plotly (over vega lite and Co), more help, more customization

+ TODO/idea
--------

- try using Timeline component
- https://discuss.streamlit.io/t/reusable-timeline-component-with-demo-for-history-of-nlp/9639
"""


# maybe later, could be rendered as a timeline
#

"""
Rendering tables with Streamlit Ag Grid, currently not used but kept as exemples
"""


def ag_render_session(df_session, CONF):
    """Rendering layer to matches history (history = --usually, several session tables)

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
        width="100%",  # not sure it is working ^_^
        fit_columns_on_grid_load=False,  #  if true, expand columns sizes to fill the whole grid width
    )


def ag_render_last_session(last_stats, CONF):
    """Ag Grid rendering layer to last session stats, as a table"""

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
        width="10%",  # not sure it is working ^_^
        fit_columns_on_grid_load=False,
    )


"""
Rendering tables with Plotly, **currently in use**
"""


def render_last_session(last_stats, gamertag, CONF):
    """Plotly rendering layer to last session aggregated stats, as a table"""

    # tighter our data(frame)
    last_stats["K D A"] = utils.concat_cols(
        last_stats, to_concat=["kills", "deaths", "assists"], sep=" | "
    )
    last_stats["Damage avg"] = utils.concat_cols(
        last_stats, to_concat=["damageDone", "damageTaken"], sep=" | "
    )
    # Rename our columns according to CONF file
    last_stats = last_stats.rename(columns=CONF.get("APP_DISPLAY").get("labels"))

    # Generate table with Plotly
    fill_colors = [
        "#ffebf5" if username == gamertag else "white"
        for username in last_stats["Player(s)"].tolist()
    ]
    font_color = [
        [
            "rgb(230,10,120)" if username == gamertag else "#31333F"
            for username in list(last_stats["Player(s)"])
        ],
        "#31333F",
        "#31333F",
    ]

    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[15, 7, 12, 7, 7, 7],
                header=dict(
                    values=[
                        "<b>Player(s)</b>",
                        "<b>Matches</b>",
                        "<b> Best Loadout</b>",
                        "<b>KD</b>",
                        "<b>K D A</b>",
                        "<b>Gulag</b>",
                    ],  # header cols names, rename here if wanted
                    align=["left"],
                    line_color="lightgrey",
                    fill_color="#F5F7F7",
                    font=dict(color="#767783", size=14),
                    # style_header={"fontWeight": "bold"},
                    height=30,
                ),
                cells=dict(
                    values=[
                        last_stats["Player(s)"],
                        last_stats["Matches"],
                        last_stats["loadoutBest"],
                        last_stats["KD"],
                        last_stats["K D A"],
                        last_stats["Gulag"],
                    ],
                    align="left",
                    format=[
                        "",
                        "",
                        "",
                        ".2f",
                        "",
                        "",
                    ],  # format columns values with d3 format
                    # fill_color=[fill_colors],
                    fill_color=["rgb(255,255,255)"],
                    line_color="lightgrey",
                    # font=dict(color="#31333F", size=14),
                    font_color=font_color,
                    font_size=14,
                    height=25,
                ),
            )
        ]
    )

    # to narrow spaces between several figures / components
    height = len(last_stats) * 30 + 40
    fig.update_layout(width=600, height=height, margin=dict(l=1, r=0, b=0, t=1))

    config = {"displayModeBar": False}
    st.plotly_chart(
        fig, use_container_width=True, config=config
    )  # True, to bypass width setting and fit to st layout


def render_team(team_kills, gamertag):
    """Render Team KDA concat with Team Weapons, in a plotly table"""

    team_kills["K D A"] = utils.concat_cols(
        team_kills, to_concat=["kills", "deaths", "assists"], sep=" | "
    )
    cols_to_concat = team_kills.columns[
        team_kills.columns.str.startswith("Loadout")
    ].tolist()
    team_kills["Loadouts"] = utils.concat_cols(
        team_kills, to_concat=cols_to_concat, str_join=", "
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

    players_kills["K D A"] = utils.concat_cols(
        players_kills, to_concat=["kills", "deaths", "assists"], sep=" | "
    )

    cols_to_concat = players_kills.columns[
        players_kills.columns.str.startswith("Loadout")
    ].tolist()
    players_kills["K D A"] = utils.concat_cols(
        players_kills, to_concat=cols_to_concat, sep=", "
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


"""
Misc streamlit "hacky-iiiish" ways to display data
"""


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


"""
Rendering charts with Plotly
"""


def render_kd_history(df):
    """Render KD and Cumulative KD of last matches"""

    y_axis = ["kdRatioRollAvg", "kdRatioCum"]
    labels = ["Mov. avg (5)", "cumulative"]
    colors = ["rgb(204, 204, 204)", "rgb(230,10,120)"]

    mode_size = [12, 8]  # node size
    line_size = [1, 3]

    fig = go.Figure()
    config = {"displayModeBar": False}  # remove modebar (produced with plotly etc.)

    # lines
    # raw kd ratio
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[y_axis[0]],
            mode="lines",
            name=labels[0],
            line=dict(color=colors[0], width=line_size[0]),
            connectgaps=True,
        )
    )
    # cum avg kd ratio
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[y_axis[1]],
            mode="lines",
            name=labels[1],
            line=dict(color=colors[1], width=line_size[1]),
            connectgaps=True,
        )
    )

    fig.update_layout(
        xaxis=dict(
            showline=True,
            showgrid=False,
            showticklabels=True,
            linecolor="rgb(204, 204, 204)",  # x axis line gris clair
            linewidth=1,
            ticks="outside",
            tickfont=dict(
                family="Arial",
                size=10,
                color="rgb(82, 82, 82)",  # x axis ticks-text gris foncé
            ),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False,
        ),
        autosize=False,
        width=400,
        height=280,
        margin=dict(
            autoexpand=False,
            l=0,
            r=0,
            t=0,  # top margin
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=0.8,
            xanchor="left",
            x=0.7,
            font=dict(size=13),
        ),
        plot_bgcolor="white",
    )

    annotations = []

    # styling : see https://plotly.com/python/text-and-annotations/#text-annotations
    # just x, y if you want to annotate a particular data point

    # Source (under x axis)
    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=0.5,
            y=-0.1,
            xanchor="center",
            yanchor="top",
            text="n last matches",
            font=dict(family="Arial", size=11, color="rgb(150,150,150)"),
            showarrow=False,
        )
    )
    # title (not a true plotly chart title "title=", but an annotation 'emulating' a title)
    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=1,
            y=1,
            xanchor="auto",
            yanchor="auto",
            text=f"k/d: {round(df['kdRatioCum'].iat[-1],2)}",
            bgcolor="rgb(230,10,120)",
            # bordercolor="black",
            borderpad=2,
            borderwidth=2,
            font=dict(family="Arial", size=15, color="rgb(255,255,255)"),
            showarrow=False,
        )
    )

    fig.update_layout(annotations=annotations)
    st.plotly_chart(
        fig, use_container_width=True, config=config
    )  # True if you wantr to bypass width setting


def render_kd_history_small(df, col):
    """Render KD and Cumulative KD of last matches as Plotly Scatter lines"""

    axis_labels = {
        "killsCumAvg": "kills avg",
        "damageDoneCumAvg": "dmg avg",
        "gulagWinPct": "gulag % win",
    }
    colors = ["darkgrey"]

    mode_size = [8]  # node size
    line_size = [2]

    fig = go.Figure()
    config = {"displayModeBar": False}

    # lines
    # cumulative win pct
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col],
            mode="lines",
            name=axis_labels.get(col),
            line=dict(color=colors[0], width=line_size[0]),
            connectgaps=True,
        )
    )

    fig.update_layout(
        xaxis=dict(
            showline=True,
            showgrid=False,
            showticklabels=True,
            linecolor="rgb(204, 204, 204)",  # x axis line gris clair
            linewidth=1,
            ticks="outside",
            tickfont=dict(
                family="Arial",
                size=10,
                color="rgb(82, 82, 82)",  # x axis ticks-text gris foncé
            ),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False,
        ),
        autosize=False,
        width=400,
        height=230,
        margin=dict(
            autoexpand=False,
            l=0,
            r=0,
            t=0,  # top margin
        ),
        showlegend=False,
        plot_bgcolor="white",
    )

    annotations = []
    # title (not a true plotly chart title "title=", but an annotation 'emulating' a title)
    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=1,
            y=1,
            xanchor="auto",
            yanchor="auto",
            bgcolor="#F5F7F7",
            borderpad=2,
            borderwidth=2,
            text=f"{axis_labels.get(col)}: {round(df[col].iat[-1],2)}",
            font=dict(family="Arial", size=13, color="rgb(37,37,37)"),
            showarrow=False,
        )
    )

    fig.update_layout(annotations=annotations)
    st.plotly_chart(
        fig, use_container_width=True, config=config
    )  # True if you wantr to bypass width setting


def render_weapons(weapons, col):
    """Render Weapons as Plotly Bar Charts"""

    weapons.sort_values(by=col, ascending=True, inplace=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=weapons.weapon,
            x=weapons[col],
            orientation="h",
            name="% pick",
            marker=dict(
                color="darkgrey", line=dict(color="rgba(246, 78, 139, 1.0)", width=0)
            ),
        )
    )

    fig.update_layout(
        xaxis=dict(
            showgrid=True,
            showline=True,
            showticklabels=False,
            zeroline=False,
            domain=[0.1, 1],
        ),
        yaxis=dict(
            showgrid=True,
            showline=False,
            showticklabels=True,
            zeroline=False,
            tickfont=dict(
                family="Arial",
                size=12,
                color="rgb(82, 82, 82)",
            ),  # x axis ticks-text gris foncé
        ),
        paper_bgcolor="rgb(255, 255, 255)",
        plot_bgcolor="rgb(255, 255, 255)",
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        width=400,
        height=230,
    )
    config = {"displayModeBar": False}
    st.plotly_chart(
        fig, use_container_width=True, config=config
    )  # True if you wantr to bypass width setting


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
