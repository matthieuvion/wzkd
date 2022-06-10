from functools import wraps
import pickle
from src import utils


def run_mode(func):
    """Decorator for app funcs that do data collection, if mode set to "offline" fetch local files

    Defined in a async manner to comply with overall app/client behavior
    Local example files (/data) are previously saved calls made to the api to each route used by the app (profile, match, matches)
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # is it an api call for profile, match or matches ?
        # add /data for when in APP code

        CONF = utils.load_conf()

        async def load_file():
            router = {
                "GetMatchStats": CONF.get("APP_BEHAVIOR")["filename"]["match"],
                "GetMoreMatchStats": CONF.get("APP_BEHAVIOR")["filename"]["match"],
                "GetMatchesDetailed": CONF.get("APP_BEHAVIOR")["filename"]["matches"],
                "GetMoreMatchesDetailed": CONF.get("APP_BEHAVIOR")["filename"][
                    "more_matches"
                ],
                "GetProfile": CONF.get("APP_BEHAVIOR")["filename"]["profile"],
            }
            filename = router[func.__name__]
            filepath = "data/" + filename
            with open(filepath, "rb") as f:
                return pickle.load(f)

        if CONF.get("APP_BEHAVIOR")["mode"] == "offline":
            return load_file()
        else:
            result = func(*args, **kwargs)
        return result

    return wrapper


def br_only(func):
    """Decorator that checks if "br_only" mode is activated in our conf (True by default)
    If so, remove matches that are not of mode 'Battle Royale' from matches result
    """
    CONF = utils.load_conf()
    LABELS = utils.load_labels()

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if CONF.get("APP_BEHAVIOR")["br_only"]:
            result = result[
                result["mode"].isin(list(LABELS.get("modes")["battle_royale"].values()))
            ]
        return result

    return wrapper
