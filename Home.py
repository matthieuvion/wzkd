import asyncio
import os
from dotenv import load_dotenv
import pickle

import pandas as pd
import httpx
import xgboost as xgb

import streamlit as st
from streamlit_option_menu import option_menu
from stqdm import stqdm

# enhanced wzlight/Api child cls to boost some wzlight client methods (caching etc.)
# from wzlight import Api
from src.enhance import EnhancedApi


from src import (
    utils,
    api_format,
    match_details,
    sessions_history,
    kd_history,
    profile_details,
    session_details,
    predict,
)

import rendering

# -------------------------- Config, credentials  ----------------------------------

# "Login" to Warzone API using wzlight wrapper
# Local app: load our SSO token (required from COD API) from local .env. See .env-template & notebooks examples for help
# Deployed app : if app deployed to share.streamlit.io, the token could be accessible via st.secrets['']
load_dotenv()
sso = os.environ["SSO"] or st.secrets("SSO")

# Wzlight api is enhanced (tweaks, caching etc..) in a separate Cls in enhance.py module
enh_api = EnhancedApi(sso)

# Load labels and global app behavior settings : run in offline mode, formatting & display options
PLATFORMS = {"Bnet": "battle", "Xbox": "xbox", "Psn": "psn", "Acti": "acti"}
CONF = utils.load_conf()
LABELS = utils.load_labels()


# ------------------------------------ Streamlit App Layout -----------------------------------------


# client runs (partly) asynchronously, thus the async-await syntax
async def main():

    # ----------------------------------------------------------#
    # Page config, Logo, session states variables               #
    # ----------------------------------------------------------#

    # Session state variables
    # I.e For streamlit not to loop if a username is not entered & searched, store last entered user...
    if "user" not in st.session_state:
        st.session_state.user = None
    if "isLogged" not in st.session_state:
        st.session_state.isLogged = None
    if "sidebar_state" not in st.session_state:
        st.session_state.sidebar_state = "expanded"

    st.set_page_config(
        page_title="Home",
        page_icon="🦊",
        layout="centered",
        initial_sidebar_state=st.session_state.sidebar_state,
    )

    # hacky way exists with css, but let's align logo to the right w/ 3 cols
    col1, col2, col3 = st.columns((0.4, 0.4, 0.1))
    with col1:
        st.write("")
    with col2:
        st.write("")
    with col3:
        st.image("data/DallE_logo_3.png", width=120, output_format="PNG")
    # st.markdown(" ")

    # ----------------------------------------------------------#
    # Sidebar / Search Player                                   #
    # ----------------------------------------------------------#

    with st.sidebar:

        # Search Player block
        st.subheader("Search Player")
        with st.form(key="loginForm"):
            col1, col2 = st.columns((1, 1.5))
            with col1:
                platform = st.selectbox(
                    "platform",
                    ["Bnet", "Xbox", "Psn", "Acti"],
                    help=""" Platform must be set accordingly to the provided user ID.  
                    I.e, user your Activision User ID is **not necessarily the same** as the one set by your preferred gaming platform (Bnet, Psn...) """,
                )
            with col2:
                # e.g usernames :
                # 1. amadevs#1689 battle, gentil_renard#3391079 acti
                # 2. gentilrenard#2939 battle, gentilrenard#9079733 acti
                username = st.text_input(
                    "user ID",
                    "amadevs#1689",
                    help=""" Check your privacy settings on callofduty.com/cod/profile so the app can retrieve your stats.  
                    Activision ID can be found in *Basic Info* and Psn/Bnet/xbox IDs in *Linked Account*.""",
                )
            submit_button = st.form_submit_button("Search")

    if username:
        st.session_state.user = username
    if submit_button:
        st.session_state.isLogged = True

    if not st.session_state.isLogged:
        st.stop()

    # If our user is already searched -> session_state['user'] or isLogged is not None anymore
    # then we can go further and call COD API
    # Could also use isLogged session state, but we're saving some options
    if st.session_state.user:
        platform = PLATFORMS.get(platform)

        # httpx client (to use with wzlight COD API wrapper) as a context manager :
        async with httpx.AsyncClient() as httpxClient:

            # ----------------------------------------------------------#
            # Search profile                                            #
            # ----------------------------------------------------------#

            # tmp patch to offline mode (load saved API responses), WZ1 API/data partly discontinued
            if not CONF["APP_BEHAVIOR"]["mode"] == "offline":
                profile = await enh_api.GetProfile(httpxClient, platform, username)
            else:
                with open("data/sample_profile.pkl", "rb") as f:
                    profile = pickle.load(f)

            # Check if callofduty profile exists (key "message" in COD API response dict."), else st.stop()
            if "message" in list(profile.keys()):
                st.warning(
                    f"Wrong platform and/or User ID ({username}). For working examples, try : (gentilrenard#2939, Bnet), (amadevs#1689, Bnet), (nicoyzovitch, Psn)"
                )
                st.stop()

            # If profile valid, carry on
            profile_kpis = profile_details.get_kpis_profile(profile)
            lifetime_kd = profile_kpis["br_kd"]
            lifetime_kills_ratio = profile_kpis["br_kills_ratio"]

            # add a little Scorecard 'Profile' in Sidebar, under Search fields
            with st.sidebar:
                st.subheader("Profile")
                username_short = username.split("#")[0]
                with st.expander(
                    f"{username_short} | lvl {profile_kpis['level']} | {profile_kpis['matches_count_all']} matches",
                    False,
                ):
                    col1, col2, col3 = st.columns((0.5, 0.5, 0.5))
                    with col1:
                        st.metric(
                            label="% mode br",
                            value=f"{profile_kpis['competitive_ratio']}%",
                        )
                    with col2:
                        st.metric(label="k/d br", value=lifetime_kd)

                    with col3:
                        st.metric(label="kills avg br", value=lifetime_kills_ratio)

            # Automatically close the Sidebar
            # if st.session_state.sidebar_state == "expanded":
            #    st.session_state.sidebar_state == "collapsed"
            #    st.experimental_rerun()

            # Create 2 containers, later filled-in with charts/tables, once we collected recent matches history
            cont_stats_history = st.container()
            cont_last_session = st.container()

            # ----------------------------------------------------------#
            # Matches (to Sessions) History                             #
            # ----------------------------------------------------------#

            # Get recent matches (history)
            st.markdown("**Play Sessions History**")
            max_calls = 5

            # tmp patch to offline mode (load saved API responses), WZ1 API/data partly discontinued
            if not CONF["APP_BEHAVIOR"]["mode"] == "offline":
                with st.spinner(
                    f"Recent matches history : collecting last {max_calls *20} matches..."
                ):
                    recent_matches = await enh_api.GetRecentMatchesWithDateLoop(
                        httpxClient, platform, username, max_calls=max_calls
                    )
            else:
                with st.spinner(
                    f"Recent matches history : collecting last {max_calls *20} matches..."
                ):
                    with open("data/sample_recent_matches.pkl", "rb") as f:
                        recent_matches = pickle.load(f)

            # in-game gamertag can be different from api username
            gamertag = utils.get_gamertag(recent_matches)

            # Extract last session match ids, for the last played match type (br/resu only)*
            last_type_ids = utils.get_last_session_ids(recent_matches)

            # Extract last game type (br or resu) played to know if we can apply our model
            # to predict avg lobby kd for our last *resurgence* matches
            last_type_played = utils.get_last_session_type(recent_matches)

            # API results are flattened, reshaped/formated, augmented (e.g. gulag W/L entry)
            recent_matches = api_format.res_to_df(recent_matches, CONF)
            recent_matches = api_format.format_df(recent_matches, CONF, LABELS)
            recent_matches = api_format.augment_df(recent_matches, LABELS)

            # Reshape our matches to a "sessions history" (gap between 2 consecutive matches > 1 hour)
            # Perform stats aggregations for each session, then render with st.aggrid
            df_sessions_history = sessions_history.to_history(
                recent_matches, CONF, LABELS
            )
            stats_sessions_history = sessions_history.stats_per_session(
                df_sessions_history
            )

            # Render each session and their stats in a stacked-two-columns layout
            # It's better to avoid rendering multi indexes tables in St, so we split them given their session idx
            sessions_indexes = df_sessions_history.session.unique().tolist()
            history_grouped = df_sessions_history.groupby("session")
            for idx in sessions_indexes:
                dict_ = stats_sessions_history.get(idx)
                df_session = history_grouped.get_group(idx)
                col1, col2 = st.columns((0.2, 0.8))
                with col1:
                    rendering.sessions_history_legend(dict_)
                with col2:
                    rendering.sessions_history_table(df_session, CONF)

            # ----------------------------------------------------------#
            # Performance History ("kd history")                        #
            # ----------------------------------------------------------#

            # Recent matches are split in 3 types (br, resu, others), in 3 separate tabs
            # They're stored in a 3-entries-dict so we won't filter afterwards & the app does not rerun
            data = {}
            types = ["Battle Royale", "Resurgence", "Others"]
            for type_ in types:
                data[type_] = utils.filter_history(recent_matches, LABELS, select=type_)

            # store last n games final-cumulative KD for each game mode in a dict, for future benchmarks
            cum_kd = kd_history.extract_last_cum_kd(data)
            st.write(cum_kd)

            with cont_stats_history:
                st.markdown("**Performance History**")

                # We want the first tab to be the most played game mode : BR or Resurgence or Others
                sort_idx = [(k, len(v)) for k, v in data.items()]
                sorted_labels = sorted(sort_idx, key=lambda x: x[1], reverse=True)
                sorted_labels = [t[0] for t in sorted_labels]

                tab1, tab2, tab3 = st.tabs(sorted_labels)

                # For every game mode, render charts in a separate tab :
                # 1 main chart (kd) on top of 2 or 3 smaller charts, organized in columns
                for tab, tab_label in zip([tab1, tab2, tab3], sorted_labels):
                    with tab:
                        # if enough data points for this game mode :
                        if len(data[tab_label]) >= 2:

                            # main chart : K/D history scatter line
                            df_kd_history = kd_history.to_history(data.get(tab_label))
                            rendering.history_kd(df_kd_history)

                            if not tab_label == "Battle Royale":
                                # small charts : Cumulative / avg given indicator, 2 cols layout
                                col1, col2 = st.columns((0.5, 0.5))
                                with col1:
                                    rendering.history_kd_small(
                                        df_kd_history, col="killsCumAvg"
                                    )
                                with col2:
                                    rendering.history_kd_small(
                                        df_kd_history, col="damageDoneCumAvg"
                                    )
                            else:
                                # small charts : Cumulative / avg given indicator, 3 cols layout
                                col1, col2, col3 = st.columns((0.5, 0.5, 0.5))
                                with col1:
                                    rendering.history_kd_small(
                                        df_kd_history, col="killsCumAvg"
                                    )
                                with col2:
                                    rendering.history_kd_small(
                                        df_kd_history, col="damageDoneCumAvg"
                                    )
                                with col3:
                                    rendering.history_kd_small(
                                        df_kd_history, col="gulagWinPct"
                                    )
                        else:
                            st.caption("Not enough matches played in recent history")

            # ----------------------------------------------------------#
            # Last Session Details                                      #
            # ----------------------------------------------------------#

            with cont_last_session:

                # Title + "fake" refresh button to rerun the loop and get the very latest matches
                col1, col2 = st.columns((9, 1))
                with col1:
                    st.markdown("**Most recent Battle Royale / Resurgence session**")
                with col2:
                    st.button("Refresh")

                # tmp patch to offline mode (load saved API responses), WZ1 API/data partly discontinued
                if not CONF["APP_BEHAVIOR"]["mode"] == "offline":
                    with st.spinner("Collecting every match of last session..."):
                        last_session = await enh_api.GetMatchList(
                            httpxClient, platform, last_type_ids
                        )
                else:
                    with st.spinner("Collecting every match of last session..."):
                        with open("data/sample_last_session.pkl", "rb") as f:
                            last_session = pickle.load(f)

                # Predict Resurgence Lobby KD (XGBoost model : from matches stats, not actual players' k/d ratios)
                # if our last match are of type Resurgence, else create a df with an empty 'lobby kd" column
                if last_type_played == "resurgence":
                    df_encoded = predict.pipeline_transform(last_session)
                    df_predicted_kd = predict.predict_lobby_kd(df_encoded)
                else:
                    n_matches = len(
                        list(set([dict_["matchID"] for dict_ in last_session]))
                    )
                    df_predicted_kd = pd.DataFrame({"Lobby KD": ["-"] * n_matches})

                # API matches stats are flattened, reshaped/formated, augmented (e.g. gulag W/L entry)
                last_session = api_format.res_to_df(last_session, CONF)
                last_session = api_format.format_df(last_session, CONF, LABELS)
                last_session = api_format.augment_df(last_session, LABELS)

                # last session matches, player stats with predicted Lobby KD appended
                n_last_matches = 3
                df_player = session_details.player_stats(last_session, gamertag)

                # render Lobbies KD + players stats & player performance bullet chart
                st.caption(
                    f"Session KD vs. last 100 games (threshold), median/mean all players this session (ticks)"
                )
                rendering.session_details_bullet_chart(
                    last_session, gamertag, last_type_played, cum_kd
                )

                st.caption(f"Last {n_last_matches} matches estimated Lobby KD")
                rendering.session_details_player_matches(
                    df_player, df_predicted_kd, CONF, n_last_matches
                )

                # last session matches stats are aggregated at last session, team level : session k/d, Best Loadout, KDA...
                teammates = session_details.get_teammates(last_session, gamertag)
                team_stats = session_details.team_aggregated_stats(
                    last_session, teammates
                )
                st.caption("Team aggregated stats:")
                rendering.session_details_aggregated(team_stats, gamertag, CONF)


if __name__ == "__main__":
    asyncio.run(main())
