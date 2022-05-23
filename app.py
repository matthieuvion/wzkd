import asyncio
import os
from dotenv import load_dotenv
import time
import itertools

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
from stqdm import stqdm

import callofduty
from callofduty import Mode, Title
from callofduty.client import Client

from src import (
    client_addons,
    utils,
    api_format,
    match_details,
    sessions_history,
    profile_details,
    session_details,
)

import app_rendering

# ------------- Customized methods for callofduty.py client, added at runtime -------------

# Defined in client_addons.py and added at runtime into callofduty.py client (Client.py class)
# All app data come from 3 endpoints : user's profile (if public), matches details, match details
# For demo purposes we can run the app in offline mode (cf conf.toml, decorators.py/@run_mode), loading local api responses examples
from src.client_addons import (
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

# Local app: load our SSO token (required from COD API) from local .env. See .env-template & notebooks examples for help
# Deployed app : if app deployed to share.streamlit.io, the token could be accessible via st.secrets['']
load_dotenv()

# Load labels and global app behavior settings : run in offline mode, formatting & display options
platform_convert = {"Bnet": "battle", "Xbox": "xbox", "Psn": "psn"}
CONF = utils.load_conf()
LABELS = utils.load_labels()


# ------------------------------------ Streamlit App Layout -----------------------------------------

# client can run asynchronously, thus the async-await syntax
async def main():

    # ---- App global config, session state user ----

    # more config : https://docs.streamlit.io/library/advanced-features/configuration#set-configuration-options
    st.set_page_config(
        page_title="wzkd",
        page_icon=None,
        layout="centered",
        initial_sidebar_state="auto",
    )

    # For streamlit not to loop if a username is not entered & searched
    if "user" not in st.session_state:
        st.session_state["user"] = None

    # ----- Sidebar -----

    with st.sidebar:
        # app title block, might add an image file later
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

    # If our user is already searched (session_state['user'] is not None anymore),
    # then we can go further and call COD API
    if st.session_state.user:

        client = await callofduty.Login(sso=os.environ["SSO"] or st.secrets("SSO"))

        # User Profile block
        st.markdown("**Profile**")

        profile = await client.GetProfile(
            platform_convert[selected_platform],
            username,
            Title.ModernWarfare,
            Mode.Warzone,
        )

        profile_kpis = profile_details.get_kpis_profile(profile)
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
                    label="% COMPETITIVE (BR)",
                    value=f"{profile_kpis['competitive_ratio']}%",
                )
            with col24:
                st.metric(label="K/D RATIO (BR)", value=lifetime_kd)
            with col25:
                st.metric(label="Kills / Match (BR)", value=lifetime_kills_ratio)
            st.caption(
                "Matches: lifetime matches all WZ modes, %Competitive : BR matches / life. matches, K/D ratio : BR Kills / Deaths"
            )

        # ----- Central part / last Session Stats (if  Battle Royale matches in our Sessions history) Scorecard -----

        # to be confirmed usage of empty() or container... (multiple elements, so pêtre meiilleur en fait)
        container_last_session = st.container()

        with container_last_session:
            st.markdown("**Last BR session performance**")

        async def retrieve_last_br_session(last_br_ids):
            last_session = []
            for br_id in stqdm(last_br_ids, desc="Retrieving matches..."):
                time.sleep(0.5)
                players_stats = await client.GetMatchStats(
                    platform_convert[selected_platform],
                    Title.ModernWarfare,
                    Mode.Warzone,
                    matchId=br_id,
                )
                last_session.extend(players_stats)

            last_session = api_format.res_to_df(last_session, CONF)
            last_session = api_format.format_df(last_session, CONF, LABELS)
            last_session = api_format.augment_df(last_session, LABELS)

            return last_session

            # st.write("placeholder last session")

        # ----- Central part Sessions History (n sessions of n matches,  default= Battle Royale only ----

        st.markdown("**Sessions History**")
        # initially we wanted to filter BR / non BR matches, but we now focus on BR matches only. No app rerun = less calls ;)
        # st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        # mode_button = st.radio("", ("All modes","Battle Royale"))
        # maybe test later : put a placeholder container above in code, and fill it with data, so when we update we replace and (maybe) not reload the
        # whole app https://discuss.streamlit.io/t/how-to-build-a-real-time-live-dashboard-with-streamlit/24437

        # idea for future : save result in session state if doable, so we do not rerun auto except if we press search again
        matches = await getMoreMatchesDetailed(
            client,
            platform_convert[selected_platform],
            username,
            Title.ModernWarfare,
            Mode.Warzone,
            n_calls=2,
        )

        matches = api_format.res_to_df(matches, CONF)
        gamertag = utils.get_gamertag(matches)

        matches = api_format.format_df(matches, CONF, LABELS)
        matches = api_format.augment_df(matches, LABELS)
        history = sessions_history.to_history(matches, CONF, LABELS)

        sessions_stats = sessions_history.stats_per_session(history)
        last_br_ids = utils.get_last_br_ids(history, LABELS)

        # render each session (a list of matches within a timespan) and their stats in a stacked-two-columns layout
        sessions_indexes = history.session.unique().tolist()
        history_grouped = history.groupby("session")
        for idx in sessions_indexes:
            dict_ = sessions_stats.get(idx)
            df_session = history_grouped.get_group(idx)
            col1, col2 = st.columns((0.2, 0.8))
            with col1:
                app_rendering.render_session_stats(dict_)
            with col2:
                app_rendering.render_session(df_session, CONF)

            # st.markdown("---")

        # ask for our latest Battle Royale matches session
        # and inject them in the --previously-empty, container placed above
        with container_last_session:
            last_session = await retrieve_last_br_session(last_br_ids)

            teammates = session_details.get_session_teammates(last_session, gamertag)
            last_stats = session_details.stats_last_session(last_session, teammates)
            app_rendering.render_last_session(last_stats, CONF)


if __name__ == "__main__":
    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
