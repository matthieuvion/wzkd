from logging import disable
import streamlit as st
import altair as alt
from st_aggrid import AgGrid

import asyncio
import os
from dotenv import load_dotenv
import pandas as pd

import callofduty
from callofduty import Mode, Title, Language
from callofduty.client import Client
from client_addons import GetMatches, GetMatchesDetailed, GetMatchesSummary, GetProfile, GetMatchStats
from match_format import MatchPlayersToDf, MatchPlayersStandardize
from matches_format import getLastMatchId, MatchesToDf, MatchesStandardize, MatchesPerDay, AggStats
from profile_format import ProfileGetKpis

# Load our SSO token (required from COD API) from local .env
load_dotenv()

# add our custom methods (addons.py) into callofduty.py client (Client.py class)
Client.GetMatches = GetMatches
Client.GetMatchesDetailed = GetMatchesDetailed
Client.GetMatchesSummary = GetMatchesSummary
Client.GetProfile = GetProfile
Client.GetMatchStats = GetMatchStats

# COD API calls, using client / our custom addons methods

platform_convert = {"Bnet":"battle", "Xbox":"xbox", "Psn":"psn"}

async def login():
    client = await callofduty.Login(sso=os.environ["SSO"])
    return client

async def getProfile(client, selected_platform, username):
    return await client.GetProfile(platform_convert.get(selected_platform), username, Title.ModernWarfare, Mode.Warzone)

async def getMatches(client, selected_platform, username):
    return await client.GetMatchesDetailed(platform_convert.get(selected_platform), username, Title.ModernWarfare, Mode.Warzone, limit=20)

async def getMatch(client, last_match_id):
    return await client.GetMatchStats('battle', Title.ModernWarfare, Mode.Warzone, matchId=last_match_id)


# Display-in-Streamlit functions

def display_matches(matches, mode_button):
    br_modes = [
        'Duos',
        'Trios',
        'Quads',
        'Iron Trials'
        ]
    df_all_matches = MatchesToDf(matches)
    df_standardized = MatchesStandardize(df_all_matches)
    modes = df_standardized['Mode'].unique().tolist() if mode_button == "All modes" else br_modes
    day_matches = MatchesPerDay(df_standardized[df_standardized['Mode'].isin(modes)])
    
    for day in day_matches.keys():
        day_stats = AggStats(day_matches[day])
        df_matches = day_matches[day]
        st.write(day)
        st.caption(
            f"{day_stats['Played']} matches - {day_stats['KD']} KD ({day_stats['Kills']} kills, {day_stats['Deaths']} deaths) - Gulag {day_stats['Gulags']} % win"
            )
        # hacks so Streamlit properly renders our (already) datetime 'End time' and already rounded 'KD' cols
        df_matches['End time'] = df_matches['End time'].astype(str)
        df_matches['KD'] = df_matches['KD'].astype(str)
        st.table(df_matches.drop('Weapons', axis=1))
        # Optional / to do / to try : render dataframes/tables as ag grid tables + customized
        # AgGrid(MatchesDisplayBasic(df_matches))

# App

async def main():

    st.set_page_config(page_title="wzkd", page_icon=None, layout="wide", initial_sidebar_state='auto')
    st.title("WZKD")
    st.caption('Warzone COD API demo app')

    if "user" not in st.session_state:
        st.session_state["user"] = None

    # Sidebar

    with st.sidebar:

        # Search Player block

        st.subheader('Search Player')
        with st.form(key='loginForm'):
            col1, col2 = st.columns((1,2))
            with col1:
                selected_platform = st.selectbox('platform', ('Bnet', 'Xbox', 'Psn'))
            with col2:
                username = st.text_input('username', 'user#1235')
                # may want to use session state here for username ?
            submit_button = st.form_submit_button('submit')
            
            # when user is searched/logged-in we keep trace of him, thru session_state
            if submit_button:
                st.session_state.user = username
        
        # Menu block

        st.sidebar.subheader('Menu')
        st.checkbox('Profile')
        st.checkbox('Historical data')
        st.checkbox('About')

        # maybe add a menu there with several "pages"

    # Main part

    # If our user is already searched/logged in :
    if st.session_state.user:
        client = await login()
        
        # User Profile block

        st.markdown('**Profile**')
        profile = await getProfile(client, selected_platform, username)
        
        with st.expander(username, True):
            kpis = ProfileGetKpis(profile)
            col11, col21, col31, col41, col51 = st.columns((0.5,0.8,0.6,0.6,0.6))
            with col11:
                st.metric(label="SEASON LVL", value=kpis['level'])
            with col21:
                st.metric(label="PRESTIGE", value=kpis['prestige'])
            with col31:
                st.metric(label="MATCHES", value=kpis['matches_count_all'])
            with col41:
                st.metric(label="% COMPETITIVE (BR)", value=f"{kpis['competitive_ratio']}%")
            with col51:
                st.metric(label="KD RATIO (BR)", value=kpis['br_kd'])
            st.caption("Matches: lifetime matches all WZ modes | Competitive : BR matches/lifetime matches | KD ratio : BR kills/deaths")
        
        # Last Match (Battle Royale only) Scorecard
        
        matches = await getMatches(client, selected_platform, username)

        st.markdown('**Last (BR) game Scorecard**')
        last_match_id = getLastMatchId(matches)
        last_match = await getMatch(client, last_match_id)

        with st.expander("Monday 10th October 23h37", True):
            df_match = MatchPlayersToDf(last_match)
            df_match_standardized = MatchPlayersStandardize(df_match)
            base = alt.Chart(df_match_standardized)         
            hist2 = base.mark_bar().encode(
                x=alt.X('Kills:Q', bin=alt.BinParams(maxbins=15)),
                y=alt.Y('count()', axis=alt.Axis(format='', title='n Players')),
                tooltip=['Kills'],
                color=alt.value("orange")
                        
            ).properties(width=250, height=300)         
            red_median_line = base.mark_rule(color='red').encode(
                x=alt.X('mean(Kills):Q', title='Kills'),
                size=alt.value(3)
            )
            st.altair_chart(hist2 + red_median_line)                
            

        # Matches History, filtered by "mode_button"

        st.markdown("**Matches History**")
        st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        mode_button = st.radio("", ("All modes","Battle Royale"))
        if mode_button == "All modes":
            display_matches(matches, mode_button)

        else:
            display_matches(matches, mode_button)




if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())