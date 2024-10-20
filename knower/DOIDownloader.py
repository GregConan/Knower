#!/usr/bin/env python3

"""
Greg Conan: gregmconan@gmail.com
Created: 2024-08-19
Updated: 2024-09-30
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
    as_HTTPS_URL, Debuggable, extract_from_json, ShowTimeTaken
)

# Constants
ABSTRACTS_FPATH = "example-publication-response.json"
DOI_2_DOMAIN = {
    "CROSSREF": "api.crossref.org/v1/works/{}",  # /transform",
    "DOI": "doi.org/{}",
    # "SCIENCEDIRECT": "https://www.sciencedirect.com/science/article/abs/pii/{}"  # TODO This doesn't use DOI in its URL
    "SPRINGER": "link.springer.com/article/{}",
    "TANDF": "www.tandfonline.com/doi/abs/{}",
    "WILEY": "onlinelibrary.wiley.com/doi/{}"
}
XML_PREFIXED_TAG = r"(?:\s?\<{1}\/?.+?:{1}.+?\>\s?)+"
# r"(?:\s?\<{1}.+?\>\s?)+" ?


def doi2url(doi: str, domain: str = "DOI", **kwargs: Any) -> str:
    """
    :param doi: str, valid DOI (Digital Object Identifier)
    :param domain: str, key in the DOI_2_DOMAIN dict, defaults to "DOI"
    :return: str, valid full URL of the specified Digital Object
    """
    return as_HTTPS_URL(DOI_2_DOMAIN[domain.upper()].format(doi), **kwargs)


def parse_abstract_from_incomplete_XML_str(abstract_txt: str) -> Dict[str, str]:
    abs_list = [x for x in filter(None, re.split(
        XML_PREFIXED_TAG, abstract_txt
    ))]  # re.split(XML_PREFIXED_TAG, abstract_txt)
    abs_dict = {"full_text": " ".join(abs_list)}
    for i in range(len(abs_list) - 1):
        if abs_list[i + 1].endswith(".") and not abs_list[i].endswith("."):
            abs_dict[abs_list[i]] = abs_list[i + 1]
    return abs_dict


class DOIDownloader(Debuggable):
    HEADERS = {"accept": "application/xml,application/xhtml+xml,text/html,*/*",
               "referer": "api.crossref.org",
               "accept-encoding": "gzip, deflate, br, zstd",
               "user-agent": HDR_USR_AGENT}

    def __init__(self, debugging: bool = False) -> None:
        self.debugging = debugging
        self.doi2resp = self.read_abstracts()  # TODO Move elsewhere?
        self.responses = list()
        self.ses = requests.Session()

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

        try:
            self.responses.append(self.ses.get(url, params=url_params,
                                               **kwargs))
            # allow_redirects=allow_redirects, timeout=timeout,
            return self.responses[-1]
        except requests.RequestException as e:
            self.debug_or_raise(e, locals())

    def download_abstract_of(self, doi: str):
        return self.download(doi2url(doi, "crossref")).json()

    def download_citation_of(self, doi: str) -> BibDatabase:
        """
        Get citation
        :param doi: str, _description_
        :return: str, _description_
        """
        resp = self.download(doi2url(doi),
                             headers={"accept": "application/x-bibtex"})
        return bibtexparser.loads(resp.text.strip())

    def get_abstract_of(self, doi: str):
        """
        _summary_ 
        :param doi: str, _description_
        """
        resp_json = self.doi2resp.get(doi)
        if not resp_json:
            resp_json = self.download_abstract_of(doi)
        try:
            abstract_txt = resp_json["message"]["abstract"].strip()
        except (KeyError, TypeError) as e:
            self.debug_or_raise(e, locals())
        try:
            # TODO add functionality to add newly downloaded abstracts to .JSON file
            abstract = parse_abstract_from_incomplete_XML_str(abstract_txt)
            assert abstract
            return abstract
        except AssertionError as e:
            self.debug_or_raise(e, locals())

    def read_abstracts(self, fpath: str = ABSTRACTS_FPATH) -> Dict[str, Any]:
        try:  # TODO Move this method to a different class?
            return extract_from_json(fpath)
        except (OSError, requests.JSONDecodeError) as e:
            print(f"Failed to read {fpath}")
            self.debug_or_raise(e, locals())
        except (AttributeError, KeyError, ValueError) as e:
            print("Unexpected err")
            self.debug_or_raise(e, locals())
