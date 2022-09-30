![WZKD logo](https://github.com/matthieuvion/wzkd/blob/master/data/DallE_logo_2.png?raw=True "Dall-E generated WZKD logo")

[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://github.com/tterb/atomic-design-ui/blob/master/LICENSEs)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)

The app is accessible [there](https://matthieuvion-wzkd-home-rqmcr9.streamlitapp.com) as it is deployed through streamlit.io.<br>

`wzkd` is a Streamlit app that collect, aggregate and visualize players' stats from Call Of Duty API (Warzone).<br>
The app is live (no database), but optimized with (partially) asynchronous calls and custom caching methods.<br>
It is the main facade which relies on two other personal projects to run :<br>
- [wzlight](https://github.com/matthieuvion/wzkd) (also on pypi) : a light, asynchronous python wrapper for 'Callof' API
- [match2kd](https://github.com/matthieuvion/match2kd) : a XGBoost model aiming at predicting game difficulty ("lobby kd") potentially saving thousands -- otherwise mandatory, API calls to players' profiles and matchs.<br>

![demo gif](https://github.com/matthieuvion/wzkd/blob/master/data/app_demo_v1.gif "demo gif")

## Features

- Use/showcase quite a lot of Streamlit features, ecosystem, "caveats" : layout options, tables, Ag Grid, Plotly, async code, caching & backoff policy using external libraries
- Data (COD API) processing and stats aggregations using Pandas. Data collection is build on top of our other project "wzlight", an async wrapper for COD API.
- No database (feature or not ^_^)), data is collected live from recent game history and a cache sytem try to prevent spamming COD API
- Warzone/CallofDuty behind-the-scene : some documentation/notebooks/bookmarks, weapons/game modes labels and parsers.

## Installation

## Usage