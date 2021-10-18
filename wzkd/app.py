from logging import disable
import streamlit as st
from st_aggrid import AgGrid

import asyncio
import os
from dotenv import load_dotenv
import pickle
import pandas as pd

import callofduty
from callofduty import Mode, Platform, Title
from callofduty.client import Client
import addons
import utils
from utils import MatchesToDf, MatchesStandardize, MatchesPerDay

st.set_page_config(layout="wide")
load_dotenv()



# caching would prevent us from init. a session every time we call COD API
# does not work right now (async issue ?)
st.experimental_singleton(suppress_st_warning=True)
def init_session():
    client = asyncio.run(callofduty.Login(sso=os.environ["SSO"]))
    return client

def display_history(matches):
    df_matches = MatchesToDf(matches)
    df_standardized = MatchesStandardize(df_matches)
    stats = MatchesPerDay(df_standardized)
    for k, v in stats.items():
        st.write(k)
        st.caption(f"{v['played']} matches - {v['kd']} KD ({v['kills']} kills, {v['deaths']} deaths) - Gulag {v['gulags']} % win")
        #AgGrid(v['matches']) 
        st.table(v['matches'])


def main():
    
    st.title("WZKD")
    st.caption('Warzone COD API demo app')

    # Sidebar
    
    with st.sidebar:
        ## Search Player block
        st.subheader('Search Player')
        with st.form(key='loginForm'):
            col1, col2 = st.columns((1,2))
            with col1:
                selected_platform = st.selectbox('platform', ('Bnet', 'Xbox', 'Psn'))
            with col2:
                selected_username = st.text_input('username', 'user#1235')
                # may want to use session state here for username ?
            submit_user = st.form_submit_button('submit')
        
        ## Navigation block
        st.sidebar.subheader('Navigation')
        st.checkbox('Profile')
        st.checkbox('Historical data')
        st.checkbox('About')

        # maybe add a menu there with several "pages"
    
    # Main

    if submit_user:
        client = init_session()
        platform_convert = {"Bnet":"battle", "Xbox":"xbox", "Psn":"psn"}
        matches = asyncio.run(
            client.GetMatchesDetailed(platform_convert.get(selected_platform), selected_username, Title.ModernWarfare, Mode.Warzone, limit=20))
        
        ## User block
        with st.expander(selected_username, False):
            st.write("lifetime stats")
            st.metric(label="KD", value="0.75", delta="0.1")
            col11, col21,col31 = st.columns((1,2,1))
            with col11:
                st.write("col 1 here") 
            with col21:
                st.write("col 2 here") 
            with col31:
                st.write("col 3 here")       
    


        ## Last Match focus
        st.markdown('**Last match Detailed Scorecard**')
        with st.expander("Monday 10th October 23h37", True):
            st.caption('to do details stat for last match played')

        ## Match History
        st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        st.markdown("**Matches History**")
        
        display = st.radio("", ('History','Sessions','Teammates'))
        if display == "History":
            display_history(matches)

        elif display == "Sessions":
            st.write('to be implemented')
        else:
            st.write('to be implemented')
        # st.table(df_matches_formated.round(2).astype("str")) # hack to round our should-already-be-rounded df

        #AgGrid(MatchesDisplayBasic(df_matches_formated))


if __name__ == '__main__':
    main()