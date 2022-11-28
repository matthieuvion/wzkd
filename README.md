![WZKD logo](https://github.com/matthieuvion/wzkd/blob/master/data/DallE_logo_3_small.png?raw=True "Dall-E generated WZKD logo")

[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://github.com/tterb/atomic-design-ui/blob/master/LICENSEs)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)

The app is accessible [there](https://matthieuvion-wzkd-home-rqmcr9.streamlitapp.com) as it is deployed through streamlit.io.<br>

`wzkd` is a Streamlit app that collect, aggregate and visualize players' stats from Call Of Duty API (Warzone 1).<br>
The app is live (no database), but optimized with (partially) asynchronous calls and custom caching methods.<br>
It is the main facade which relies on two other personal projects to run :<br>
- [wzlight](https://github.com/matthieuvion/wzlight) (also on pypi) : a light, asynchronous python wrapper for 'Callof' API
- [match2kd](https://github.com/matthieuvion/match2kd) : a XGBoost model aiming at predicting game difficulty ("lobby kd") potentially saving thousands -- otherwise mandatory, API calls to players' profiles and matchs.<br>

![demo gif](https://github.com/matthieuvion/wzkd/blob/master/data/app_demo_v2.gif "demo gif")

## What you might find useful 

- Use/showcase quite a lot of Streamlit features, ecosystem : layout options, tables vs. Ag Grid vs. Plotly, examples of customized visualizations.
- Modules and main app (Home.py) are annotated so (let's hope) you can figure what / how the whole thing is running
- Overcome some "limitations" of Streamlit, especially when working on a live project + in an async environment :  async code, caching & backoff policy using external libraries.
- No database (feature or not ^_^)), data is collected live from recent game history and a cache sytem try to prevent spamming COD API.
- Data (COD API) processing and stats aggregations using Pandas. Data collection is build on top of our other project "wzlight", an async wrapper for COD API.
- Implementation of an XGB model in the app.
- Warzone/CallofDuty behind-the-scene : some documentation/notebooks/bookmarks, weapons/game modes labels and parsers; also take a look on ressources listed underneath.
