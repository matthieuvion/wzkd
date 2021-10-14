from logging import disable
import streamlit as st

import asyncio
import os
from dotenv import load_dotenv

import callofduty
from callofduty import Mode, Platform, Title
from callofduty.client import Client
import addons
import utils
from utils import MatchesToDf, FormatMatches

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
    # st.sidebar.title("WZKD")
    st.sidebar.subheader('Player')

    with st.sidebar:
        with st.form(key='loginForm'):
            col1, col2 = st.columns(2)
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
    if submit_user_button:
        client = init_session()
        # st.write(client) # appears that our client is initiated everytime -,-

        matches =  asyncio.run(
            client.GetMatchesDetailed(
                Platform.BattleNet, selected_username, Title.ModernWarfare, Mode.Warzone, limit=20
                )
            )
        #st.header(selected_username)
        with st.expander(selected_username, False):
            st.write("lifetime stats")
            st.metric(label="KD", value="0.75", delta="0.1")

        # Last Match focus
        st.markdown('**Last match performance**')
        last_match_col1, last_match_col2, last_match_col3 = st.columns(3)
        last_match_col1.metric(label="kD", value="Plunder", delta="0.1")
        last_match_col2.metric(label="K/D/A", value="1/2/4")
        last_match_col3.metric(label="Gulag", value="W")


        # Match History
        st.markdown("**Matches History**")
        displayCol1, displayCol2, displayCol3 = st.columns(3)
        with displayCol1:
            st.checkbox("history")
        with displayCol2:
            st.checkbox("sessions")
        with displayCol3:
            st.checkbox("teammates")
        
                
        df_matches = MatchesToDf(matches)
        df_matches_formated = FormatMatches(df_matches)
        st.table(df_matches_formated)


if __name__ == '__main__':
    main()