import asyncio
import os
from weakref import WeakMethod
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
    kd_history,
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
                    Activision ID can be found in *Basic Info* and Psn/Bnet/xbox IDs in *Linked Account*.""",
                )
            submit_button = st.form_submit_button("submit")

            # when user is searched/logged-in we keep trace of him, through session_state
            # if submit_button:
            if username:
                st.session_state.user = username

        # TODO Navigation menu with option-menu OR newer st multipages feature
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

    # If our user is already searched (session_state['user'] is not None anymore),
    # then we can go further and call COD API

    # if st.session_state.user:
    # tmp/optional if not condition, but *might* be necessary when multipaging
    if not submit_button:
        st.stop()

    if submit_button:
        # flush temporary help/About
        placeholder_about.empty()
        st.session_state.about = 1

        # API credentials stored either locally or server side (share.streamlit.io)
        client = await callofduty.Login(sso=os.environ["SSO"] or st.secrets("SSO"))

        try:
            profile = await client.GetProfile(
                platform_convert[selected_platform],
                # maybe here use session_state.user
                # or add a username = session_state.user and do not change functions
                username,
                Title.ModernWarfare,
                Mode.Warzone,
            )
        except:
            st.warning(f"wrong platform and/or User ID ({username})")
            st.stop()

        profile_kpis = profile_details.get_kpis_profile(profile)
        lifetime_kd = profile_kpis["br_kd"]
        lifetime_kills_ratio = profile_kpis["br_kills_ratio"]

        # User Profile in sidebar below search block
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

        # ----- Central part / last Session Stats (if Battle Royale matches in our Sessions history) Scorecard -----

        # final layout tbc : empty() vs. container()
        # The containers will later be filled with charts/tables once we collected our matches history, gamertag, ids...
        container_kd_history = st.container()
        container_last_session = st.container()

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

        # 1.a get matches history and format COD API response. Extract User's gamertag from result
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
            matches = api_format.format_df(matches, CONF, LABELS)
            matches = api_format.augment_df(matches, LABELS)

            # In-game user' gamertag can be different from Profile, keep trace of it to personify our app
            gamertag = utils.get_gamertag(matches)

            # Cannot filter BR matches when requesting COD API, we're doing it afterwards if "true" in CONF
            matches = utils.br_only(matches, CONF, LABELS)

            # 1.b Reshape our matches to a "sessions history" (gap between 2 consecutive matches > 1 hour)
            # 1.c Perform stats aggregations for each session
            df_sessions_history = sessions_history.to_history(matches, CONF, LABELS)
            stats_sessions_history = sessions_history.stats_per_session(
                df_sessions_history
            )
            # 1.d Extract the last matches ids from our last session, later we will request the API for more detailed stats
            last_session_br_ids = utils.get_last_br_ids(df_sessions_history, LABELS)

            # 1.e Render each session (a list of matches within a certain timespan) and their stats in a stacked-two-columns layout
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
            # st.markdown("---")

        # 2.a Request COD API for detailed stats of last session's matches and reshape-augment the API response
        # 2.b render "sessions history" in a previously-created-above st.container()
        with container_last_session:

            st.markdown("**Last Session Details**")

            last_session = await GetMoreMatchStats(
                client,
                platform_convert[selected_platform],
                username,
                Title.ModernWarfare,
                Mode.Warzone,
                match_ids=last_session_br_ids,
                n_max=8,
            )
            last_session = api_format.res_to_df(last_session, CONF)
            last_session = api_format.format_df(last_session, CONF, LABELS)
            last_session = api_format.augment_df(last_session, LABELS)

            teammates = session_details.get_session_teammates(last_session, gamertag)
            last_stats = session_details.stats_last_session(last_session, teammates)
            weapons = session_details.get_players_weapons(last_session)

            rendering.render_last_session(last_stats, gamertag, CONF)
            with st.expander("in construction....more details", False):
                st.caption("Session Players' Picks")
                rendering.render_weapons(weapons, col="pickRate")

        # 3. render kd history chart(s) in a previously-created-above st.container()
        with container_kd_history:

            st.markdown("**Battle Royale Stats History**")

            df_kd = kd_history.to_history(matches)
            rendering.render_kd_history(df_kd)

            col1, col2, col3 = st.columns((0.5, 0.5, 0.5))
            with col1:
                rendering.render_kd_history_small(df_kd, idx=0)
            with col2:
                rendering.render_kd_history_small(df_kd, idx=1)
            with col3:
                rendering.render_kd_history_small(df_kd, idx=2)


if __name__ == "__main__":
    asyncio.run(main())
