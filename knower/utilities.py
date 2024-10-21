
#!/usr/bin/env python3

"""
Lower-level utilities and convenience functions for multiple Knower files' use
Greg Conan: gregmconan@gmail.com
Created: 2024-07-26
Updated: 2024-09-30
"""
# Import standard libraries
from collections.abc import Callable
import datetime as dt
import json
import logging
import os
import pdb
import requests
import sys
from typing import Any, Hashable, Iterable, Mapping, Optional

# Import third-party libraries from PyPI

# Constants
DOI_2_DOMAIN = {
    "CROSSREF": "api.crossref.org/v1/works/{}",  # /transform",
    "DOI": "doi.org/{}",
    # "SCIENCEDIRECT": "https://www.sciencedirect.com/science/article/abs/pii/{}"  # TODO This doesn't use DOI in its URL
    "SPRINGER": "link.springer.com/article/{}",
    "TANDF": "www.tandfonline.com/doi/abs/{}",
    "WILEY": "onlinelibrary.wiley.com/doi/{}"
}
LOGGER_NAME = __name__


# NOTE All functions below are in alphabetical order.

def as_HTTPS_URL(*parts: str, **url_params: Any) -> str:
    """
    Re-usable convenience function to build URLs
    :param parts: Iterable[str] of slash-separated URL path parts
    :param url_params: Mapping[str, Any] of variable names and their values
                       to pass to the API endpoint as parameters
    :return: String, full HTTPS URL path
    """
    str_params = [f"{k}={v}" for k, v in url_params.items()]
    url = f"https://{'/'.join(parts)}"
    if str_params:
        url += "?" + "&".join(str_params)
    return url


def debug(an_err: Exception, local_vars: Mapping[str, Any]) -> None:
    """
    :param an_err: Exception (any)
    :param local_vars: Dict[str, Any] mapping variables' names to their
                       values; locals() called from where an_err originated
    """
    locals().update(local_vars)
    if verbosity_is_at_least(2):
        logging.getLogger(LOGGER_NAME).exception(an_err)  # .__traceback__)
    if verbosity_is_at_least(1):
        show_keys_in(locals())  # , logging.getLogger(LOGGER_NAME).info)
    pdb.set_trace()


class Debuggable:
    # I put the debugger function in a class so it can use its
    # implementer classes' self.debugging variable
    def debug_or_raise(self, an_err: Exception, local_vars: Mapping[str, Any]
                       ) -> None:
        """
        :param an_err: Exception (any)
        :param local_vars: Dict[str, Any] mapping variables' names to their
                           values; locals() called from where an_err originated
        :raises an_err: if self.debugging is False; otherwise pause to debug
        """
        if self.debugging:
            debug(an_err, local_vars)
        else:
            raise an_err


def default_pop(poppable: Any, key: Any = None,
                default: Any = None) -> Any:
    """
    :param poppable: Any object which implements the .pop() method
    :param key: Input parameter for .pop(), or None to call with no parameters
    :param default: Object to return if running .pop() raises an error
    :return: Object popped from poppable.pop(key), if any; otherwise default
    """
    try:
        to_return = poppable.pop() if key is None else poppable.pop(key)
    except (AttributeError, IndexError, KeyError):
        to_return = default
    return to_return


def doi2url(doi: str, domain: str = "DOI", **kwargs: Any) -> str:
    """
    :param doi: str, valid DOI (Digital Object Identifier)
    :param domain: str, key in the DOI_2_DOMAIN dict, defaults to "DOI"
    :return: str, valid full URL of the specified Digital Object
    """
    return as_HTTPS_URL(DOI_2_DOMAIN[domain.upper()].format(doi), **kwargs)


def download_GET(path_URL: str, headers: Mapping[str, Any]) -> Any:
    """
    :param path_URL: String, full URL path to a file/resource to download
    :param headers: Mapping[str, Any] of header names to their values in the
                    HTTP GET request to send to path_URL
    :return: Object(s) retrieved from path_URL using HTTP GET request
    """
    # Make the request to the API
    response = requests.get(path_URL, headers=headers)

    # Check if the request was successful
    try:
        assert response.status_code == 200
        return response
    except (AssertionError, requests.JSONDecodeError) as err:
        # TODO replace print with log
        print(f"\nFailed to retrieve file(s) at {path_URL}\n"
              f"{response.status_code} Error: {response.reason}")


def extract_from_json(json_path):
    """
    :param json_path: String, a valid path to a real readable .json file
    :return: Dictionary, the contents of the file at json_path
    """
    with open(json_path, 'r') as infile:
        return json.load(infile)


# TODO Replace "print()" calls with "log()" calls after making log calls
#      display in the Debug Console window when running pytest tests
def log(content: str, level: int = logging.INFO,
        logger_name: str = LOGGER_NAME) -> None:
    """
    :param content: String, the message to log/display
    :param level: int, the message's importance/urgency/severity level as
                  defined by logging module's 0 (ignore) to 50 (urgent) scale
    """
    logging.getLogger(logger_name).log(msg=content, level=level)


# TODO move to debug_tools?
def show_keys_in(a_dict: Mapping[str, Any],  # show: Callable = log
                 what_keys_are: str = "Local variables",
                 level: int = logging.INFO) -> None:
    """
    :param a_dict: Dictionary mapping strings to anything
    :param log: Function to log/print text, e.g. logger.info or print
    :param what_keys_are: String naming what the keys are
    """
    log(f"{what_keys_are}: {stringify_list(uniqs_in(a_dict))}", level=level)


def stringify_list(a_list: list) -> str:
    """
    :param a_list: List (any)
    :return: String containing all items in a_list, single-quoted and
             comma-separated if there are multiple
    """
    result = ""
    if a_list and isinstance(a_list, list):
        list_with_str_els = [str(el) for el in a_list]
        if len(a_list) > 1:
            result = "'{}'".format("', '".join(list_with_str_els))
        else:
            result = list_with_str_els[0]
    return result


class ShowTimeTaken:
    # TODO Use "log" instead of "print" by default
    def __init__(self, doing_what: str, show: Callable = print) -> None:
        """
        Context manager to time and log the duration of any block of code
        :param doing_what: String describing what is being timed
        :param show: Function to print/log/show messages to the user
        """
        self.doing_what = doing_what
        self.show = show

    def __call__(self):
        """
        Explicitly defining __call__ as a no-op to prevent instantiation
        """
        pass

    def __enter__(self):
        """
        Log the moment that script execution enters the context manager and
        what it is about to do.
        """
        self.start = dt.datetime.now()
        self.show(f"Started {self.doing_what} at {self.start}")
        return self

    def __exit__(self, exc_type: Optional[type] = None,
                 exc_val: Optional[BaseException] = None, exc_tb=None):
        """
        Log the moment that script execution exits the context manager and
        what it just finished doing.
        :param exc_type: Exception type
        :param exc_val: Exception value
        :param exc_tb: Exception traceback
        """
        self.elapsed = dt.datetime.now() - self.start
        self.show(f"\nTime elapsed {self.doing_what}: {self.elapsed}")


class SplitLogger(logging.getLoggerClass()):
    # Container class for message-logger and error-logger ("split" apart)
    FMT = "\n%(levelname)s %(asctime)s: %(message)s"
    LVL = dict(OUT={logging.DEBUG, logging.INFO},
               ERR={logging.CRITICAL, logging.ERROR, logging.WARNING})
    NAME = LOGGER_NAME

    def __init__(self, verbosity: int, out: Optional[str] = None,
                 err: Optional[str] = None) -> None:
        """
        Make logger to log status updates, warnings, and other important info.
        SplitLogger can log errors/warnings/problems to one stream/file and
        log info/outputs/messages to a different stream/file.
        :param verbosity: Int, the number of times that the user included the
                          --verbose flag when they started running the script.
        :param out_fpath: Valid path to text file to write output logs into
        :param err_fpath: Valid path to text file to write error logs into
        """  # TODO stackoverflow.com/a/33163197 ?
        super().__init__(self.NAME, level=verbosity_to_log_level(verbosity))
        self.addSubLogger("out", sys.stdout, out)
        self.addSubLogger("err", sys.stderr, err)

    @classmethod
    def from_cli_args(cls, cli_args: Mapping[str, Any]) -> "SplitLogger":
        """
        Get logger, and prepare it to log to a file if the user said to
        :param cli_args: Mapping[str, Any] of command-line input arguments
        :return: SplitLogger
        """
        log_to = dict()
        if cli_args.get("log"):
            log_file_name = f"log_{stringify_dt(dt.datetime.now())}.txt"
            log_file_path = os.path.join(cli_args["log"], log_file_name)
            log_to = dict(out=log_file_path, err=log_file_path)
        return cls(verbosity=cli_args["verbosity"], **log_to)

    def addSubLogger(self, sub_name: str, log_stream,
                     log_file_path: Optional[str] = None):
        """
        Make a child Logger to handle one kind of message (namely err or out)
        :param name: String naming the child logger, accessible as
                     self.getLogger(f"{self.NAME}.{sub_name}")
        :param log_stream: io.TextIOWrapper, namely sys.stdout or sys.stderr
        :param log_file_path: Valid path to text file to write logs into
        """
        sublogger = self.getChild(sub_name)
        sublogger.setLevel(self.level)
        handler = (logging.FileHandler(log_file_path, encoding="utf-8")
                   if log_file_path else logging.StreamHandler(log_stream))
        handler.setFormatter(logging.Formatter(fmt=self.FMT))
        sublogger.addHandler(handler)

    @classmethod
    def logAtLevel(cls, level: int, msg: str) -> None:
        """
        Log a message, using the sub-logger specific to that message's level 
        :param level: logging._levelToName key; level to log the message at
        :param msg: String, the message to log
        """
        logger = logging.getLogger(cls.NAME)
        if level in cls.LVL["ERR"]:
            sub_log_name = "err"
        elif level in cls.LVL["OUT"]:
            sub_log_name = "out"
        sublogger = logger.getChild(sub_log_name)
        sublogger.log(level, msg)


def stringify_dt(moment: dt.datetime) -> str:
    """
    :param moment: datetime, a specific moment
    :return: String, that moment in "YYYY-mm-dd_HH-MM-SS" format
    """
    return moment.isoformat(sep="_", timespec="seconds"
                            ).replace(":", "-")  # .strftime("%Y-%m-%d_%H-%M-%S")


def uniqs_in(listlike: Iterable[Hashable]) -> list:
    """
    Get an alphabetized list of unique, non-private local variables' names
    by calling locals() and then passing it into this function
    :param listlike: List-like collection (or dict) of strings
    :return: List (sorted) of all unique strings in listlike that don't start
             with an underscore
    """
    uniqs = set([v if not v.startswith("_") else None
                 for v in listlike]) - {None}
    uniqs = [x for x in uniqs]
    uniqs.sort()
    return uniqs


def utcnow() -> dt.datetime:
    """
    :return: datetime.datetime, the moment that this function was called,
             set to the UTC timezone
    """
    return dt.datetime.now(tz=dt.timezone.utc)


# TODO Maybe move into new "Loggable" class?
def verbosity_to_log_level(verbosity: int) -> int:
    """
    :param verbosity: Int, the number of times that the user included the
                      --verbose flag when they started running the script.
    :return: Level for logging, corresponding to verbosity like so:
             verbosity == 0 corresponds to logging.ERROR(==40)
             verbosity == 1 corresponds to logging.WARNING(==30)
             verbosity == 2 corresponds to logging.INFO(==20)
             verbosity >= 3 corresponds to logging.DEBUG(==10)
    """
    return max(10, 40 - (10 * verbosity))


def verbosity_is_at_least(verbosity: int) -> bool:
    """
    :param verbosity: Int, the number of times that the user included the
                      --verbose flag when they started running the script.
    :return: Bool indicating whether the program is being run in verbose mode
    """
    return logging.getLogger().getEffectiveLevel() \
        <= verbosity_to_log_level(verbosity)


def wrap_with_params(call: Callable, *args: Any, **kwargs: Any) -> Callable:
    """
    Define values to pass into a previously-defined function ("call"), and
    return that function object wrapped with its new preset/default values
    :param call: Callable, function to add preset/default parameter values to
    :return: Callable, "call" with preset/default values for the 'args' and
             'kwargs' parameters, so it only accepts one positional parameter
    """
    # TODO Convert to decorator?
    return lambda x: call(x, *args, **kwargs)
