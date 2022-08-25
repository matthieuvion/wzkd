import asyncio
import os
from weakref import WeakMethod
from dotenv import load_dotenv
import time
import itertools

import pandas as pd
import httpx

import streamlit as st
from streamlit_option_menu import option_menu
from stqdm import stqdm

from wzlight import Api

# enhanced Api child cls to boost some wzlight Api methods (add caching etc.)
from src.enhance import EnhancedApi


from src import (
    utils,
    api_format,
    match_details,
    sessions_history,
    kd_history,
    profile_details,
    session_details,
)

import rendering

# -------------------------- Config, credentials  ----------------------------------


# "Login" to Warzone API using wzlight wrapper
# Local app: load our SSO token (required from COD API) from local .env. See .env-template & notebooks examples for help
# Deployed app : if app deployed to share.streamlit.io, the token could be accessible via st.secrets['']
load_dotenv()
sso = os.environ["SSO"] or st.secrets("SSO")
api = Api(sso)

# Wzlight api is enhanced (tweaks, caching etc..) in a separate Cls in enhance.py module
enh_api = EnhancedApi(sso)

# Load labels and global app behavior settings : run in offline mode, formatting & display options
PLATFORMS = {"Bnet": "battle", "Xbox": "xbox", "Psn": "psn", "Acti": "acti"}
CONF = utils.load_conf()
LABELS = utils.load_labels()


# ------------------------------------ Streamlit App Layout -----------------------------------------


# client runs (partly) asynchronously, thus the async-await syntax
async def main():

    st.set_page_config(
        page_title="Home",
        page_icon="🦊",
        layout="centered",
        initial_sidebar_state="auto",
    )

    st.image("data/wzkd3.png", width=130)
    # st.image("data/dallE_fox_1.png", width=70)
    st.markdown(" ")
    st.markdown(" ")

    # For streamlit not to loop if a username is not entered & searched
    if "user" not in st.session_state:
        st.session_state.user = None

    # Sidebar

    with st.sidebar:

        # Search Player block
        st.subheader("Search Player")
        with st.form(key="loginForm"):
            col1, col2 = st.columns((1, 1.5))
            with col1:
                platform = st.selectbox(
                    "platform",
                    ("Bnet", "Xbox", "Psn", "Acti"),
                    help=""" Platform must be set accordingly to the provided user ID.  
                    I.e, user your Activision User ID is **not necessarily the same** as the one set by your preferred gaming platform (Bnet, Psn...) """,
                )
            with col2:
                username = st.text_input(
                    "user ID",
                    "amadevs#1689",
                    help=""" Check your privacy settings on callofduty.com/cod/profile so the app can retrieve your stats.  
                    Activision ID can be found in *Basic Info* and Psn/Bnet/xbox IDs in *Linked Account*.""",
                )
            submit_button = st.form_submit_button("submit")

    if username:
        st.session_state.user = username

    # Optional
    if not submit_button:
        st.stop()

    # If our user is already searched -> session_state['user'] is not None anymore
    # then we can go further and call COD API

    if st.session_state.user:
        platform = PLATFORMS.get(platform)

        # httpx client (to use with wzlight COD API wrapper) as a context manager :
        async with httpx.AsyncClient() as httpxClient:

            # Call/Check if User's COD profile exists (or is public)
            try:
                # Default call, without our app enhancements would be profile = await api.GetProfile()
                profile = await enh_api.GetProfileCached(
                    httpxClient, platform, username
                )
            except:
                st.warning(f"wrong platform and/or User ID ({username})")
                st.stop()

            profile_kpis = profile_details.get_kpis_profile(profile)
            lifetime_kd = profile_kpis["br_kd"]
            lifetime_kills_ratio = profile_kpis["br_kills_ratio"]

            # add a little Scorecard 'Profile' in Sidebar, under Search fields
            with st.sidebar:
                st.subheader("Profile")

                with st.expander(
                    f"{username} | lvl {profile_kpis['level']} | {profile_kpis['matches_count_all']} matches",
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

            # Create 2 containers, later filled-in with charts/tables, once we collected matches history
            cont_stats_history = st.container()
            cont_last_session = st.container()

            with cont_stats_history:
                st.markdown("**Stats History**")
                # TODO : sorted list so most played type is displayed first
                list_ = ["Battle Royale", "Resurgence", "Others"]
                tab1, tab2, tab3 = st.tabs(list_)
                # filled-in later, once we collected recent matches (history)

            with cont_last_session:
                st.markdown("**Last Session Details**")
                # filled-in later once we collected detailed stats for n recent matches (last session)

            # -----------------------------------------------------------#
            # Block Match History : matches/stats grouped per session    #
            # -----------------------------------------------------------#

            # Get recent matches (history)
            st.markdown("**Sessions History**")
            with st.spinner("Collecting (BR) matches history..."):
                recent_matches = await enh_api.GetRecentMatchesWithDateLoop(
                    httpxClient, platform, username, max_calls=2
                )
            # in-game gamertag can be different from in-stats gamertag
            gamertag = utils.get_gamertag(recent_matches)

            # Extract last session match ids, for the last played type (br/resu only)*
            last_type_ids = utils.get_last_session_ids(recent_matches)

            # API results are flattened, reshaped/formated, augmented (e.g. gulag W/L entry)
            recent_matches = api_format.res_to_df(recent_matches, CONF)
            recent_matches = api_format.format_df(recent_matches, CONF, LABELS)
            recent_matches = api_format.augment_df(recent_matches, LABELS)

            # Reshape our matches to a "sessions history" (gap between 2 consecutive matches > 1 hour)
            # Perform stats aggregations for each session, then render with st.aggr
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
                    rendering.render_session_stats(dict_)
                with col2:
                    rendering.ag_render_session(df_session, CONF)

            # ----------------------------------------------------------#
            #   Block Last Session Details                              #
            # ----------------------------------------------------------#

            # st.markdown("---")

            # Recent matches are split in 3 types (br, resu, others)
            # API results are flattened, reshaped, formated, augmented (+ gulag W/L entry)
            # and stored in a dic with 3 entries  : we wont filter afterwards, so the app does not rerun
            # data = {}
            # types = ["br", "resu", "others"]
            # for type_ in types:
            #     data[type_] = utils.filter_history(recent_matches, select=type_)
            #     if len(data[type_]) >= 2:
            #         data[type_] = api_format.res_to_df(data[type_], CONF)
            #         data[type_] = api_format.format_df(data[type_], CONF, LABELS)
            #         data[type_] = api_format.augment_df(data[type_], LABELS)
            #     else:
            #         data[type_] = None

            # convert to sessions (> 1h between 2 matches), aggregate

            # st.write(data)


if __name__ == "__main__":
    asyncio.run(main())
