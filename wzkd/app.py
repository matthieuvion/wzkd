from logging import disable
import streamlit as st
from st_aggrid import AgGrid

import asyncio
import os
from dotenv import load_dotenv

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


def main():
    
    # Sidebar

    with st.sidebar:
        st.subheader('Search Player')
        with st.form(key='loginForm'):
            col1, col2 = st.columns((1,2))
            with col1:
                selected_platform = st.selectbox('platform', ('Bnet', 'Xbox', 'PlaySt'))
            with col2:
                selected_username = st.text_input('username', 'user#1235')
                # may want to use session state here for username ?
            submit_user_button = st.form_submit_button('submit')

        st.sidebar.subheader('Navigation')
        st.checkbox('Profile')
        st.checkbox('Historical data')
        st.checkbox('About')
#    if submit_user_button:
#        with st.expander("Lifetime Profile", False):
#            st.write('add lifetime stats here')


#
        # maybe add a menu there with several "pages"
    
    # Main

    st.title("WZKD")
    st.caption('Warzone COD API demo app')
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
    
    if submit_user_button:
        client = init_session()
        # st.write(client) # appears that our client is initiated everytime -,-
    
        matches =  asyncio.run(
            client.GetMatchesDetailed(
                Platform.BattleNet, selected_username, Title.ModernWarfare, Mode.Warzone, limit=20
                )
            )
        

        # Last Match focus
        st.markdown('**Last match Detailed Scorecard**')
        with st.expander("Monday 10th October 23h37", True):
            st.caption('to do details stat for last match played')

        # Match History
        st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        st.markdown("**Matches History**")
        
        matches_display = st.radio(label = '', options = ['History','Sessions','Teammates'])
        if matches_display == "History":
            df_matches = MatchesToDf(matches)
            df_matches_formated = MatchesStandardize(df_matches)
            dict_dfs = MatchesPerDay(df_matches_formated)
            for key, value in dict_dfs.items():
                st.write(key)
                st.table(value)
        if matches_display == "Sessions":
            st.caption('to be implemented')
        if matches_display == "Teammates":
            st.caption('to be implemented')
        # st.table(df_matches_formated.round(2).astype("str")) # hack to round our should-already-be-rounded df

        #AgGrid(MatchesDisplayBasic(df_matches_formated))


if __name__ == '__main__':
    main()