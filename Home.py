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
from callofduty.http import HTTP

from src import (
    utils,
    api_format,
    match_details,
    sessions_history,
    profile_details,
    session_details,
)

import rendering

# ------------- Customized methods/edits of callofduty.py client, added at runtime -------------

# Defined in client_addons.py and added at runtime into callofduty.py client
# All app data come from 3 main endpoints :
# user's profile (must be public), matches details (matches history with stats), match details

from src.client_addons import (
    GetMatches,
    GetMatchesDetailed,
    GetMoreMatchesDetailed,
    GetMatchStats,
    GetMoreMatchStats,
    GetProfile,
    Send,
)

# callofduty.py edited methods, added at runtime
Client.GetMatches = GetMatches
Client.GetMatchesDetailed = GetMatchesDetailed
Client.GetProfile = GetProfile
Client.GetMatchStats = GetMatchStats
HTTP.Send = Send

# -------------------------- Config, credentials  ----------------------------------

# Local app: load our SSO token (required from COD API) from local .env. See .env-template & notebooks examples for help
# Deployed app : if app deployed to share.streamlit.io, the token could be accessible via st.secrets['']
load_dotenv()

# Load labels and global app behavior settings : run in offline mode, formatting & display options
platform_convert = {"Bnet": "battle", "Xbox": "xbox", "Psn": "psn", "Acti": "uno"}
CONF = utils.load_conf()
LABELS = utils.load_labels()


# ------------------------------------ Streamlit App Layout -----------------------------------------

# client can run asynchronously, thus the async-await syntax
async def main():

    # App global config, Session States

    # more config options see:
    # https://docs.streamlit.io/library/advanced-features/configuration#set-configuration-options
    # Or demo Apps : https://streamlit.io/gallery

    st.set_page_config(
        page_title="Home",
        page_icon="🦊",
        layout="centered",
        initial_sidebar_state="auto",
    )

    # title (logo)
    st.image("data/wzkd3.png", width=130)
    st.markdown(" ")
    st.markdown(" ")
    # Probably later : add tooltip to 'search user here 👈 " and maybe "demo mode => offline"

    # For streamlit not to loop if a username is not entered & searched
    if "user" not in st.session_state:
        st.session_state.user = None
    if "about" not in st.session_state:
        st.session_state.about = None

    # Sidebar

    with st.sidebar:

        # Search Player block
        st.subheader("Search Player")
        with st.form(key="loginForm"):
            col1, col2 = st.columns((1, 1.5))
            with col1:
                selected_platform = st.selectbox(
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
                    Activision ID can be found in *Basic Info* and Psn/Bnet/xbox in *Linked Account*.""",
                )
            submit_button = st.form_submit_button("submit")

            # when user is searched/logged-in we keep trace of him, through session_state
            # if submit_button:
            if username:
                st.session_state.user = username

        # TODO Navigation menu with option-menu or newer st multipages feature
        # menu = option_menu(
        #    " ",
        #    ["Home", "Settings"],
        #    icons=["house", "gear"],
        #    menu_icon="cast",
        #    default_index=1,

    # Temporary Home : App help / About

    placeholder_about = st.empty()
    if not st.session_state.about:
        with placeholder_about.container():
            # TODO better syntax and overall design + content
            st.markdown("#")
            st.subheader("**Getting Started**")
            # might change, now uno/Activision seems to work
            started_text = """
            👈 Enter your User ID and your platform on the sidebar menu.  
            Your profile must be public so this app or other trackers can retrieve your stats.  
            If not, go to callofduty.com/cod/profile/ *"privacy settings"* tab and opt in to *"available to 3rd party"*.  
            
            Note that your User or Activision ID can differ from in-game username, notably if you changed it in the past. You can retrieve them under in-game settings for your gaming platform or callofduty.com *"basic info"* & *"Linked Accounts"* tabs.
            """
            st.markdown(started_text)
            st.markdown("#")
            st.subheader("**Hunder the Hood**")
            st.markdown("...")

    # Central part

    # ----- Central part / Profile -----

    # If our user is already searched (session_state['user'] is not None anymore),
    # then we can go further and call COD API

    # if st.session_state.user:
    # optional if not condition, but *might* be necessary when multipaging
    if not submit_button:
        st.stop()

    if submit_button:
        # flush temporary help/About
        placeholder_about.empty()
        st.session_state.about = 1

        client = await callofduty.Login(sso=os.environ["SSO"] or st.secrets("SSO"))

        # User Profile block
        st.markdown("**Profile**")

        profile = await client.GetProfile(
            platform_convert[selected_platform],
            # maybe here use session_state.user
            # or add a username = session_state.user and do not change functions
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
                    label="% BR matchs",
                    value=f"{profile_kpis['competitive_ratio']}%",
                )
            with col24:
                st.metric(label="K/D RATIO (BR)", value=lifetime_kd)
            with col25:
                st.metric(label="Kills / Match (BR)", value=lifetime_kills_ratio)
            st.caption(
                "Matches: lifetime matches all WZ modes, % Battle Royale matches / all matches, K/D ratio : BR Kills / Deaths"
            )

        # ----- Central part / last Session Stats (if Battle Royale matches in our Sessions history) Scorecard -----

        # final layout tbc : empty() vs. container()
        # This container will be filled after matches history + last session match ids data collection
        container_last_session = st.container()
        with container_last_session:
            st.markdown("**Last Session Details**")

        # ----- Central part Sessions History (n sessions of n matches,  default= Battle Royale only ----

        st.markdown("**Sessions History**")
        # initially we wanted to be able to filter BR / non BR matches, but no app rerun = less calls ;)
        # Also cannot st.cache / experimental with async architecture
        # TODO (maybe) : put a placeholder container above in code, and fill it with data, so when we update we replace and (maybe) not reload the
        # whole app https://discuss.streamlit.io/t/how-to-build-a-real-time-live-dashboard-with-streamlit/24437 or :

        # idea for future : save result in session state if doable, so we do not rerun auto except if we press search again
        # https://discuss.streamlit.io/t/how-to-save-the-displayed-dataframe-after-user-select-from-the-selectbox-using-st-session-state/14694/5
        # a refresh button would reset its value (maybe stored in session_state as well)
        # or firebase ;)
        with st.spinner("Collecting (BR) matches history..."):
            matches = await GetMoreMatchesDetailed(
                client,
                platform_convert[selected_platform],
                username,
                Title.ModernWarfare,
                Mode.Warzone,
                min_br_matches=20,
            )
            # TODO :(more) error handling in case of API failure ...if matches... :
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
                    rendering.render_session_stats(dict_)
                with col2:
                    rendering.ag_render_session(df_session, CONF)
            # st.markdown("---")

        # ask for our latest Battle Royale matches session
        # and inject them in the --previously-empty, container placed above
        with container_last_session:
            # last_session = await retrieve_last_br_session(last_br_ids)
            last_session = await GetMoreMatchStats(
                client,
                platform_convert[selected_platform],
                username,
                Title.ModernWarfare,
                Mode.Warzone,
                match_ids=last_br_ids,
                n_max=8,
            )
            last_session = api_format.res_to_df(last_session, CONF)
            last_session = api_format.format_df(last_session, CONF, LABELS)
            last_session = api_format.augment_df(last_session, LABELS)

            teammates = session_details.get_session_teammates(last_session, gamertag)
            last_stats = session_details.stats_last_session(last_session, teammates)
            rendering.render_last_session(last_stats, gamertag, CONF)


if __name__ == "__main__":
    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
