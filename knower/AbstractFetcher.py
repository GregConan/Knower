#!/usr/bin/env python3

"""
Greg Conan: gregmconan@gmail.com
Created: 2024-08-19
Updated: 2024-10-21
"""
# Import standard libraries
import pdb
import re
import requests
from typing import Any, Dict, List, Literal, Mapping, Optional
# import xml.etree.ElementTree as etree

# Import 3rd-party PyPI libraries
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
# import crossref_commons.retrieval as crossref_API
# import crossref_commons.types as crossref_ORM

# Local custom imports
from knower.constants import (
    EMAIL, HDR_USR_AGENT
)
from knower.utilities import (
    doi2url, Debuggable, extract_from_json, ShowTimeTaken
)

# Constants
ABSTRACTS_FPATH = "example-publication-response.json"
XML_PREFIXED_TAG = r"(?:\s?\<{1}\/?.+?:{1}.+?\>\s?)+"
# r"(?:\s?\<{1}.+?\>\s?)+" ?


def parse_abstract_from_incomplete_XML_str(abstract_txt: str
                                           ) -> Dict[str, str]:
    abs_list = [x for x in filter(None, re.split(
        XML_PREFIXED_TAG, abstract_txt
    ))]  # re.split(XML_PREFIXED_TAG, abstract_txt)
    abs_dict = {"full_text": " ".join(abs_list)}
    for i in range(len(abs_list) - 1):
        if abs_list[i + 1].endswith(".") and not abs_list[i].endswith("."):
            abs_dict[abs_list[i]] = abs_list[i + 1]
    return abs_dict


class Downloader(Debuggable):
    def __init__(self, debugging: bool = False) -> None:
        self.debugging = debugging
        self.responses = list()
        self.ses = requests.Session()

    def get(self, url: str | bytes,
            # allow_redirects: bool = True, timeout: int = 10,
            # headers: Mapping[str, str] = {...},
            url_params: Mapping[str, str],
            **kwargs: Any) -> requests.Response:
        try:
            self.responses.append(self.ses.get(url, params=url_params,
                                               **kwargs))
            # allow_redirects=allow_redirects, timeout=timeout,
            return self.responses[-1]
        except requests.RequestException as err:
            self.debug_or_raise(err, locals())


class AbstractFetcher(Downloader):
    HEADERS: Dict[str, str] = {
        "accept": "application/xml,application/xhtml+xml,text/html,*/*",
        "referer": "api.crossref.org",
        "accept-encoding": "gzip, deflate, br, zstd",
        "user-agent": HDR_USR_AGENT
    }

    def __init__(self, fpath: Optional[str] = ABSTRACTS_FPATH,
                 debugging: bool = False) -> None:
        super().__init__(debugging=debugging)
        self.doi2resp = self.read_from_file(fpath)  # TODO Move elsewhere?

    def download(self, url: str | bytes,
                 # allow_redirects: bool = True, timeout: int = 10,
                 # headers: Mapping[str, str] = {...},
                 url_params: Mapping[str, str] = {"mailto": EMAIL},
                 **kwargs: Any) -> requests.Response:
        # Default parameters for REST request
        # kwargs.setdefault("params", {"mailto": EMAIL})
        kwargs.setdefault("allow_redirects", True)
        kwargs.setdefault("timeout", 10)

        # Default headers for REST request; overwrite with any new ones
        kwargs["headers"] = {**self.HEADERS, **kwargs.get("headers", dict())}
        return self.get(url, url_params, **kwargs)

    def download_crossref(self, doi: str) -> dict | None:  # TODO ?
        return self.download(doi2url(doi, "crossref")).json()

    def download_bibtex(self, doi: str) -> BibDatabase:
        """
        Get citation
        :param doi: str, _description_
        :return: str, _description_
        """
        resp = self.download(doi2url(doi),
                             headers={"accept": "application/x-bibtex"})
        return bibtexparser.loads(resp.text.strip())

    def fetch(self, doi: str) -> Dict[str, str]:
        """
        _summary_ 
        :param doi: str, _description_
        """
        resp_json = self.doi2resp.get(doi)
        if not resp_json:
            resp_json = self.download_crossref(doi)
        try:
            abstract_txt = resp_json["message"]["abstract"].strip()
        except (KeyError, TypeError) as err:
            self.debug_or_raise(err, locals())
        try:
            # TODO add functionality to add newly downloaded abstracts to .JSON file
            abstract = parse_abstract_from_incomplete_XML_str(abstract_txt)
            assert abstract
            return abstract
        except AssertionError as err:
            self.debug_or_raise(err, locals())

    def read_from_file(self, fpath: str) -> Dict[str, Any]:
        try:  # TODO Move this method to a different class?
            return extract_from_json(fpath)
        except (OSError, requests.JSONDecodeError) as err:
            print(f"Failed to read {fpath}")
            self.debug_or_raise(err, locals())
        except (AttributeError, KeyError, ValueError) as err:
            print("Unexpected err")
            self.debug_or_raise(err, locals())
