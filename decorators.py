from functools import wraps
from re import S
import utils
import pickle


def run_mode(func):
    """
    Decorator that checks if "offline" mode is activated in our conf
    If so, do not call COD API but load local example files (/data), depending on func name called by app
    Function is defined in a async manner to comply with overall client behavior
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # is it an api call for profile, match or matches ?
        # add /data for when in APP code

        CONF = utils.load_conf()

        async def load_file():
            router = {
                "GetMatchStats": CONF.get("APP_BEHAVIOR")["filename"]["match"],
                "GetMatchesDetailed": CONF.get("APP_BEHAVIOR")["filename"]["matches"],
                "getMoreMatchesDetailed": CONF.get("APP_BEHAVIOR")["filename"][
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
    """
    Decorator that checks if "br_only" mode is activated in our conf (True by default)
    If so, remove matches that are not of mode 'Battle Royale' from our matches result
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
