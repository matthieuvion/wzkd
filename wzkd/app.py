import asyncio
from calendar import c
import os
import pickle
from re import M
from webbrowser import get
from dotenv import load_dotenv

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
import altair as alt
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder

import callofduty
from callofduty import Mode, Title
from callofduty.client import Client

import utils
import api_format
import kpis_match, sessions_history, kpis_profile


# ------------- Customized methods to callofduty.py client, added at runtime -------------

# Defined in client_addons.py and added at runtime into callofduty.py client (Client.py class)
# All app data come from 3 endpoints : user's profile (if public), matches, match details
# For demo purposes we can run the app in offline mode (cf conf.toml, decorators.py/@run_mode), loading local api responses examples
from client_addons import (
    GetMatches,
    GetMatchesDetailed,
    getMoreMatchesDetailed,
    GetMatchesSummary,
    GetMatchStats,
    GetProfile,
)

Client.GetMatches = GetMatches
Client.GetMatchesDetailed = GetMatchesDetailed
Client.GetMatchesSummary = GetMatchesSummary
Client.GetProfile = GetProfile
Client.GetMatchStats = GetMatchStats

# -------------------------- Config files, credentials  ----------------------------------

# Load our SSO token (required from COD API) from local .env. See .env-template & notebooks examples for help
load_dotenv()

# Load labels and global app behavior settings : run in offline mode, formatting & display options
platform_convert = {"Bnet": "battle", "Xbox": "xbox", "Psn": "psn"}
CONF = utils.load_conf()
LABELS = utils.load_labels()


# ---------------------- Functions to display our Data nicely in Streamlit ----------------------

# We define them now to lighten up the app layout code further below
# Also, some hacks/tricks must be applied to better display our dataframes in streamlit


# idea, render as a timeline :
# https://discuss.streamlit.io/t/reusable-timeline-component-with-demo-for-history-of-nlp/9639
def render_session_table(df_session, CONF):
    """
    Final layer applied to our list of matches with stats, to render them "well" in our app
    Streamlit or even AgGrid does not render well dfs with a multi index, aka : blank rows etc.)
    We structure and display our data differently : one df => dfs grouped by session + print of sessions aggregated stats
    Maybe later some cell highlights cf. https://discuss.streamlit.io/t/ag-grid-component-with-input-support/8108/184
    """

    # tighter our data(frame)
    df_session["K D A"] = utils.concat_cols(
        df_session, to_concat=["kills", "deaths", "assists"], sep="."
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
        df_session,
        gridOptions=gb.build(),
        height=height,  # hard coded height, works well for default aggrid theme
        width="100%",
        fit_columns_on_grid_load=False,
    )


# gb.configure_column("date_tz_aware", type=["dateColumnFilter","customDateTimeFormat"], custom_format_string='yyyy-MM-dd HH:mm zzz', pivot=True)


def render_session_stats(dict_):
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


# ------------------------------------ Streamlit App Layout -----------------------------------------

# client can run asynchronously, thus the async-await syntax
async def main():

    # ---- Title, user session state ----

    # more config : https://docs.streamlit.io/library/advanced-features/configuration#set-configuration-options
    st.set_page_config(
        page_title="wzkd",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="auto",
    )

    # For streamlit not to loop, if one username is not entered & searched
    if "user" not in st.session_state:
        st.session_state["user"] = None

    # ----- Sidebar -----

    with st.sidebar:
        # app title block
        st.title("WZKD")
        st.caption("Warzone COD API demo app")

        # Search Player block
        st.subheader("Search Player")
        with st.form(key="loginForm"):
            col1, col2 = st.columns((1, 2))
            with col1:
                selected_platform = st.selectbox("platform", ("Bnet", "Xbox", "Psn"))
            with col2:
                username = st.text_input("username", "e.g. amadevs#1689")
                # may want to use session state here for username ?
            submit_button = st.form_submit_button("submit")

            # when user is searched/logged-in we keep trace of him, through session_state
            if submit_button:
                st.session_state.user = username

        # Navigation menu with option-menu , try to get several pages later
        # try menu option streamlit component
        # menu = option_menu(
        #    " ",
        #    ["Home", "Settings"],
        #    icons=["house", "gear"],
        #    menu_icon="cast",
        #    default_index=1,
        # )
        # menu basic version with st.checkbox
        # st.sidebar.subheader("Menu")
        # st.checkbox('Home')
        # st.checkbox('Last BR detailed')
        # st.checkbox('Historical data')
        # st.checkbox('About')po

    # ----- Central part / Profile -----

    # If our user is already searched (session_state['user'] is None),
    # then we can go further and call COD API
    if st.session_state.user:

        client = await callofduty.Login(sso=os.environ["SSO"])

        # User Profile block
        st.markdown("**Profile**")

        profile = await client.GetProfile(
            platform_convert[selected_platform],
            username,
            Title.ModernWarfare,
            Mode.Warzone,
        )

        profile_kpis = kpis_profile.get_kpis_profile(profile)
        lifetime_kd = profile_kpis["br_kd"]
        lifetime_kills_ratio = profile_kpis["br_kills_ratio"]
        with st.expander(username, True):
            col21, col22, col23, col24, col25 = st.columns((0.5, 0.6, 0.6, 0.6, 0.6))
            with col21:
                st.metric(label="SEASON LVL", value=profile_kpis["level"])
            with col22:
                st.metric(label="MATCHES", value=profile_kpis["matches_count_all"])
            with col23:
                st.metric(
                    label="% COMPETITIVE (BR matches)",
                    value=f"{profile_kpis['competitive_ratio']}%",
                )
            with col24:
                st.metric(label="K/D RATIO (BR)", value=lifetime_kd)
            with col25:
                st.metric(label="Kills / Match (BR)", value=lifetime_kills_ratio)
            st.caption(
                "Matches: lifetime matches all WZ modes, %Competitive : BR matches / life. matches, K/D ratio : BR Kills / Deaths"
            )
            # ----- Central part / Last Match (if a Battle Royale) Scorecard -----

        # matches = await client.GetMatchesDetailed(
        #    platform_convert[selected_platform],
        #    username,
        #    Title.ModernWarfare,
        #    Mode.Warzone,
        # )
        # if CONF.

        # idea for future : save result in session state if doable, so we do not rerun auto except if we press search again
        matches = await getMoreMatchesDetailed(
            client,
            platform_convert[selected_platform],
            username,
            Title.ModernWarfare,
            Mode.Warzone,
            n_calls=2,
        )
        gamertag = utils.get_gamer_tag(matches)
        #        br_id = utils.get_last_match_id(matches)
        #
        #        if br_id:
        #
        #            #match = await get_match(client, br_id)
        #            match = await client.GetMatchStats(
        #               platform_convert[selected_platform],
        #               username,
        #               Title.ModernWarfare,
        #               Mode.Warzone,
        #                matchId = br_id
        #               )
        #
        #            match = api_format.res_to_df(match, CONF)
        #            match = api_format.format_df(match, CONF, LABELS)
        #            match_date, match_mode = utils.get_date(match), utils.get_mode(match)
        #
        #            st.markdown("**Last BR Scorecard**")
        #            # st.caption(f"{match_date} ({match_mode})")
        #            with st.expander(f"{match_date} ({match_mode})", True):
        #
        #                # Last Match : first layer of stats (team main metrics)
        #
        #                col31, col32, col33 = st.columns((1, 1, 1))
        #                with col31:
        #                    placement = kpis_match.get_placement(match, gamertag)
        #                    st.metric(label="PLACEMENT", value=f"{placement}")
        #
        #                with col32:
        #                    tkp = kpis_match.teamKillsPlacement(match, gamertag)
        #                    st.metric(label="TEAM KILLS RANK", value=f"{tkp+1}")
        #
        #                with col33:
        #                    tpk = kpis_match.teamPercentageKills(match, gamertag)
        #                    st.metric(label="TEAM % ALL KILLS", value=f"{tpk}%")
        #
        #                # Last Match : 2nd layer of stats (team info : kills, team weapons)
        #                # st.markdown("""---""")
        #                col41, col42 = st.columns((1, 1))
        #                with col41:
        #                    team_kills = kpis_match.teamKills(match, gamertag, LABELS)
        #                    render_team(team_kills, gamertag)
        #
        #                with col42:
        #                    players_quartiles = kpis_match.playersQuartiles(match)
        #                    player_kills = kpis_match.get_player_kills(match, gamertag)
        #                    render_bullet_chart(
        #                        lifetime_kd,
        #                        lifetime_kills_ratio,
        #                        player_kills,
        #                        players_quartiles,
        #                    )
        #                st.caption(
        #                    "Goal/Threshold : lifetime kills or kd | comparisons : game players' median (< 50% players), mean, 3rd quartile (< 75%), max"
        #                )
        #
        #            with st.expander("Match details", False):
        #                col51, col52 = st.columns((1, 1))
        #                with col51:
        #                    players_kills = kpis_match.topPlayers(match, LABELS)
        #                    render_players(players_kills)
        #
        #                with col52:
        #                    base = alt.Chart(match)
        #                    hist2 = (
        #                        base.mark_bar()
        #                        .encode(
        #                            x=alt.X("Kills:Q", bin=alt.BinParams(maxbins=15)),
        #                            y=alt.Y(
        #                                "count()", axis=alt.Axis(format="", title="n Players")
        #                            ),
        #                            tooltip=["Kills"],
        #                            color=alt.value("orange"),
        #                        )
        #                        .properties(width=250, height=200)
        #                    )
        #                    red_median_line = base.mark_rule(color="red").encode(
        #                        x=alt.X("mean(Kills):Q", title="Kills"), size=alt.value(3)
        #                    )
        #                    st.altair_chart(hist2 + red_median_line)

        # ----- Central part / Matches (Battle Royale mode only by default) History -----

        st.markdown("**Sessions History**")
        # initially we wanted to filter BR / non BR matches, but we now focus on BR matches only. Consume less calls ;)
        # st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        # mode_button = st.radio("", ("All modes","Battle Royale"))
        # maybe test later : put a placeholder container above in code, and fill it with data, so when we update we replace and (maybe) not reload the
        # whole app https://discuss.streamlit.io/t/how-to-build-a-real-time-live-dashboard-with-streamlit/24437

        matches = api_format.res_to_df(matches, CONF)
        matches = api_format.format_df(matches, CONF, LABELS)
        matches = api_format.augment_df(matches, LABELS)

        history = sessions_history.to_history(matches, CONF, LABELS)
        sessions_stats = sessions_history.stats_per_session(history)

        # render each session (a list of matches) and their stats in a stacked-two-columns layout
        sessions_indexes = history.session.unique().tolist()
        history_grouped = history.groupby("session")
        for idx in sessions_indexes:
            dict_ = sessions_stats.get(idx)
            df_session = history_grouped.get_group(idx)
            col1, col2 = st.columns((0.2, 0.8))
            with col1:
                render_session_stats(dict_)
            with col2:
                render_session_table(df_session, CONF)

            # st.markdown("---")


if __name__ == "__main__":
    CONF = utils.load_conf()
    LABELS = utils.load_labels()
    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
