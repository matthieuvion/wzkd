import streamlit as st
import altair as alt
import plotly.graph_objects as go
from st_aggrid import AgGrid

from logging import disable
import os
from dotenv import load_dotenv
import asyncio
import pandas as pd

import callofduty
from callofduty import Mode, Title
from callofduty.client import Client
from client_addons import GetMatches, GetMatchesDetailed, GetMatchesSummary, GetProfile, GetMatchStats

import matches_format
import match_format
import profile_format

# ------------- Our custom methods to callofduty.py client, added at runtime -------------
    
# Defined in client_addons.py and added into callofduty.py client (Client.py class)

Client.GetMatches = GetMatches
Client.GetMatchesDetailed = GetMatchesDetailed
Client.GetMatchesSummary = GetMatchesSummary
Client.GetProfile = GetProfile
Client.GetMatchStats = GetMatchStats

# -------------------------- Functions to fetch data from COD API --------------------------
    
# COD API calls, using callofduty.py client with our (minor) tweaks
# All data come from 3 endpoints : user's profile (if public), matches, match details

# Load our SSO token (required from COD API) from local .env
load_dotenv()

async def login():
    client = await callofduty.Login(sso=os.environ["SSO"])
    return client

platform_convert = {"Bnet":"battle", "Xbox":"xbox", "Psn":"psn"}

async def getProfile(client, selected_platform, username):
    return await client.GetProfile(
        platform_convert.get(selected_platform), username, Title.ModernWarfare, Mode.Warzone
        )

async def getMatches(client, selected_platform, username):
    return await client.GetMatchesDetailed(
        platform_convert.get(selected_platform), username, Title.ModernWarfare, Mode.Warzone, limit=20
        )

async def getMatch(client, last_match_id):
    return await client.GetMatchStats(
        'battle', Title.ModernWarfare, Mode.Warzone, matchId=last_match_id
        )

# ---------------------- Functions to display our Data nicely in Streamlit ----------------------

# We define them now to lighten up the app layout code below
# Also, some hacks/tricks must be applied to better display our df in streamlit

def renderMatches(matches, mode_button):
    """ Render Matches History, Day : list of matches that day"""
    br_modes = [
        'Duos',
        'Trios',
        'Quads',
        'Iron Trials'
        ]
    df_all_matches = matches_format.MatchesToDf(matches)
    df_standardized = matches_format.MatchesStandardize(df_all_matches)
    modes = df_standardized['Mode'].unique().tolist() if mode_button == "All modes" else br_modes
    day_matches = matches_format.MatchesPerDay(df_standardized[df_standardized['Mode'].isin(modes)])
    
    for day in day_matches.keys():
        day_stats = matches_format.AggStats(day_matches[day])
        df_matches = day_matches[day]
        st.write(day)
        st.caption(
            f"{day_stats['Played']} matches - {day_stats['KD']} KD ({day_stats['Kills']} kills, {day_stats['Deaths']} deaths) - Gulag {day_stats['Gulags']} % win"
            )
        # hacks (int to str) so Streamlit properly renders our (already) datetime 'End time' and already rounded 'KD' cols
        df_matches[['End time', 'KD']] = df_matches[['End time', 'KD']].astype(str)
        st.table(df_matches.drop('Weapons', axis=1))
        # Optional : render using AgGrid component e.g AgGrid(MatchesDisplayBasic(df_matches))

def shrinkDf(df, cols_to_concat, str_join, new_col):
    """ For our df to occupy less space in Streamlit : to str + concat given cols into 1"""
    
    def concat_cols(df, cols_to_concat, str_join):
        return pd.Series(map(str_join.join, df[cols_to_concat].values.tolist()),index = df.index)
    
    for col in cols_to_concat:
        df[col] = df[col].astype(str)
    df[new_col] = concat_cols(df, cols_to_concat, str_join)
    df = df.drop(cols_to_concat, axis=1)
    
    return df

def renderTeam(team_kills, team_weapons):
    """ Render Team' KDA concat. with Team' Weapons, in a plotly table"""

    team_kills = shrinkDf(team_kills, cols_to_concat=['Kills', 'Deaths', 'Assists'], str_join=' | ', new_col= 'K D A')
    team_weapons = shrinkDf(team_weapons, cols_to_concat=['Loadout_1', 'Loadout_2', 'Loadout_3'], str_join=', ', new_col='Loadouts')
        
    team_weapons.reset_index().drop('index', axis=1)
    pad_row = {'Username': 'Team', 'Loadouts': '-'}
    team_weapons = team_weapons.append(pad_row, ignore_index=True)
    team_weapons = team_weapons.drop('Username', axis=1)
    team_info = pd.concat([team_kills, team_weapons], axis=1, sort=True)
    team_info = team_info.rename(columns={"Username": "Player"})
    # here clean concatenated weapons columns
    
    # plot with plotly
    fig = go.Figure(
        data=[
            go.Table(
                columnwidth = [30, 15, 20, 60],
                header = dict(values=list(team_info.columns),
                          align=['left'],
                          line_color='#F0F2F6',
                          fill_color='white'),
                cells = dict(values=[team_info.Player, team_info.KD, team_info['K D A'], team_info.Loadouts],
                            align='left',
                            fill_color='white',
                            font_size=14))
        ]
    )

    # to narrow spaces between several figures
    fig.update_layout(
        width=600,
        height=150,
        margin=dict(
            l=0,
            r=0,
            b=0,
            t=0
            )
        )
    st.plotly_chart(fig, use_container_width=True)   
    #st.dataframe(team_info)
    # hack remove index, but keep empty col still : st.dataframe(team_info.assign(hack='').set_index('hack'))

def renderPlayers(players_kills):
    """ Render Game top Kills players in a plotly table """

    players_kills = shrinkDf(players_kills, cols_to_concat=['Kills', 'Deaths', 'Assists'], str_join=' | ', new_col= 'K D A')
    players_kills = shrinkDf(players_kills, cols_to_concat=['Loadout_1', 'Loadout_2', 'Loadout_3'], str_join=', ', new_col= 'Loadouts')
    players_kills = players_kills.rename(columns={"Username": "Player"})

    # plot with plotly
    fig = go.Figure(
        data=[
            go.Table(
                columnwidth = [30, 20, 15, 20, 60],
                header = dict(values=list(players_kills.columns),
                          align=['left'],
                          line_color='#F0F2F6',
                          fill_color='white'),
                cells = dict(values=[players_kills.Player, players_kills.Team, players_kills.KD, players_kills['K D A'], players_kills.Loadouts],
                            align='left',
                            fill_color='white',
                            font_size=14))
        ]
    )

    # to narrow spaces between several figures
    fig.update_layout(
        width=600,
        height=250,
        margin=dict(
            l=0,
            r=0,
            b=0,
            t=0
            )
        )
    st.plotly_chart(fig, use_container_width=True)   

def renderBulletChart(lifetime_kd, player_kills, players_quartiles):
    """ Renders Players KD bullet chart"""

    kd_player = player_kills['KD'] if not player_kills['KD'] == 0 else 0.1
    kd_mean = round(players_quartiles['KD']['mean'], 1)
    kd_median = round(players_quartiles['KD']['50%'],1)
    kd_Q3 = round(players_quartiles['KD']['75%'],1)
    kd_max = int(players_quartiles['KD']['max'])
    gauge_length = 4

    fig = go.Figure(go.Indicator(
        mode = "number+gauge+delta", value = kd_player,
        domain = {'x': [0.1, 1], 'y': [0, 1]},
        title = {'text' :"KD", 'font_size':15},
        delta = {'reference': lifetime_kd},
        gauge = {
            'shape': "bullet",
            'axis': {'range': [None, gauge_length]},
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': lifetime_kd},
            'steps': [
                {'range': [0, kd_median], 'color': "grey"},
                {'range': [kd_median, kd_mean], 'color': "darkgrey"},
                {'range': [kd_mean, kd_Q3], 'color': "lightgrey"}],
            'bar': {'color': "black"}
        }))

    fig.update_layout(
        height = 70,
        width = 400,
        margin = {'t':0, 'b':30, 'l':0}
    )
    ticks = [kd_median, kd_mean, kd_Q3, gauge_length]
    fig.update_traces(
        gauge={
            "axis": {
                "tickmode": "array",
                "tickvals": ticks,
                "ticktext": [f"...{kd_max}" if i == gauge_length else i for i in ticks],
            }
        }
    )
    st.plotly_chart(fig, use_container_width=True)   

# ------------------------------------ Streamlit App Layout -----------------------------------------

# client can run asynchronously, thus the async, await syntax
async def main():

    # ---- Title, user session state ----

    st.set_page_config(page_title="wzkd", page_icon=None, layout="wide", initial_sidebar_state='auto')
    st.title("WZKD")
    st.caption('Warzone COD API demo app')

    if "user" not in st.session_state:
        st.session_state["user"] = None

    # ----- Sidebar -----

    with st.sidebar:
        # Search Player block
        st.subheader('Search Player')
        with st.form(key='loginForm'):
            col1, col2 = st.columns((1,2))
            with col1:
                selected_platform = st.selectbox('platform', ('Bnet', 'Xbox', 'Psn'))
            with col2:
                username = st.text_input('username', 'e.g. amadevs#1689')
                # may want to use session state here for username ?
            submit_button = st.form_submit_button('submit')
            
            # when user is searched/logged-in we keep trace of him, thru session_state
            if submit_button:
                st.session_state.user = username
        
        # Navigation menu

        st.sidebar.subheader('Menu')
        #st.checkbox('Home')
        #st.checkbox('Last BR detailed')
        #st.checkbox('Historical data')
        #st.checkbox('About')

        # maybe add a menu there with several "pages"

    # ----- Central part / Profile -----

    # If our user is already searched/logged in :
    if st.session_state.user:
        client = await login()
        
        # User Profile block
        st.markdown('**Profile**')
        
        profile = await getProfile(client, selected_platform, username)
        profile_kpis = profile_format.ProfileGetKpis(profile)
        lifetime_kd = profile_kpis['br_kd']
        
        with st.expander(username, True):
            col21, col22, col23, col24, col25 = st.columns((0.5,0.8,0.6,0.6,0.6))
            with col21:
                st.metric(label="SEASON LVL", value=profile_kpis['level'])
            with col22:
                st.metric(label="PRESTIGE", value=profile_kpis['prestige'])
            with col23:
                st.metric(label="MATCHES", value=profile_kpis['matches_count_all'])
            with col24:
                st.metric(label="% COMPETITIVE (BR)", value=f"{profile_kpis['competitive_ratio']}%")
            with col25:
                st.metric(label="KD RATIO (BR)", value=lifetime_kd)
            st.caption("Matches: lifetime matches all WZ modes, %Competitive : BR matches / life. matches, KD ratio : BR Kills / Deaths")
        
    # ----- Central part / Last Match (BR) Scorecard -----
        
        matches = await getMatches(client, selected_platform, username)
        
        gamertag = matches_format.getGamertag(matches)
        br_id = matches_format.getLastMatchId(matches)
        
        if br_id:
            
            match = await getMatch(client, br_id)
            
            match = match_format.MatchPlayersToDf(match)
            match = match_format.MatchPlayersStandardize(match)
            match_date, match_mode = match_format.retrieveDate(match), match_format.retrieveMode(match)

            st.markdown("**Last BR Scorecard**")
            #st.caption(f"{match_date} ({match_mode})")
            with st.expander(f"{match_date} ({match_mode})", True):
            
            # Last Match : first layer of stats (team main metrics)
            
                col31, col32, col33  = st.columns((1,1,1))
                with col31:
                    placement = match_format.retrievePlacement(match, gamertag)
                    st.metric(label = "PLACEMENT", value=f"{placement}")

                with col32:
                    tkp = match_format.teamKillsPlacement(match, gamertag)
                    st.metric(label = "TEAM KILLS RANK", value=f"{tkp+1}")

                with col33:
                    tpk = match_format.teamPercentageKills(match, gamertag)
                    st.metric(label = "TEAM % ALL KILLS", value=f"{tpk}%")
            
            # Last Match : 2nd layer of stats (team info : kills, team weapons)
                #st.markdown("""---""")
                col41, col42  = st.columns((1,1))
                with col41:
                    team_kills = match_format.teamKills(match, gamertag)
                    team_weapons = match_format.teamWeapons(match, gamertag)
                    renderTeam(team_kills, team_weapons)

                with col42:
                    players_quartiles = match_format.playersQuartiles(match)
                    player_kills = match_format.retrievePlayerKills(match, gamertag)
                    renderBulletChart(lifetime_kd, player_kills, players_quartiles)
                    
            with st.expander("GAME STATS", False):
                col51, col52 = st.columns((1,1))    
                with col51:
                    players_kills = match_format.topPlayers(match)
                    renderPlayers(players_kills)               
                
                with col52:
                    base = alt.Chart(match)         
                    hist2 = base.mark_bar().encode(
                        x=alt.X('Kills:Q', bin=alt.BinParams(maxbins=15)),
                        y=alt.Y('count()', axis=alt.Axis(format='', title='n Players')),
                        tooltip=['Kills'],
                        color=alt.value("orange")
                                
                    ).properties(width=250, height=200)         
                    red_median_line = base.mark_rule(color='red').encode(
                        x=alt.X('mean(Kills):Q', title='Kills'),
                        size=alt.value(3)
                    )
                    st.altair_chart(hist2 + red_median_line)


        # ----- Central part / Matches History -----

        st.markdown("**Matches History**")
        # hack to displau radio button horizontally
        st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        mode_button = st.radio("", ("All modes","Battle Royale"))
        if mode_button == "All modes":
            renderMatches(matches, mode_button)

        else:
            renderMatches(matches, mode_button)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())