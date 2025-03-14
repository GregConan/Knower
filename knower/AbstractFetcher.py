#!/usr/bin/env python3

"""
Greg Conan: gregmconan@gmail.com
Created: 2024-08-19
Updated: 2025-03-13
"""
# Import standard libraries
import pdb
import re
import urllib.parse
import requests
from typing import Any, Dict, List, Literal, Mapping, Optional
import xml.etree.ElementTree as ElementTree

# Import 3rd-party PyPI libraries
# import crossref_commons.retrieval as crossref_API
# import crossref_commons.types as crossref_ORM
import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
import bs4
from elsapy.elsdoc import AbsDoc
import pybliometrics.scopus as scopus
from pybliometrics.scopus.exception import ScopusException
import requests.cookies
import tldextract
import urllib

# Import remote custom libraries
from gconanpy.debug import Debuggable, ShowTimeTaken
from gconanpy.IO.local import extract_from_json
from gconanpy.seq import as_HTTPS_URL

# Import local custom libraries and constants
try:
    from constants import DOI_2_DOMAIN, ELSA_API_KEY, EMAIL, HDR_USR_AGENT
    from elsa import Searcher
except ModuleNotFoundError:
    from knower.constants import DOI_2_DOMAIN, ELSA_API_KEY, EMAIL, HDR_USR_AGENT
    from knower.elsa import Searcher

# Constants
ABSTRACTS_FPATH = "example-publication-response.json"
HTTP_HEADERS = {"accept-encoding": "gzip, deflate, br, zstd",
                "user-agent": HDR_USR_AGENT}
XML_PREFIXED_TAG = r"(?:\s?\<{1}\/?.+?:{1}.+?\>\s?)+"
# r"(?:\s?\<{1}.+?\>\s?)+" ?


def doi2url(doi: str, domain: str = "DOI", **kwargs: Any) -> str:
    """
    :param doi: str, valid DOI (Digital Object Identifier)
    :param domain: str, key in the DOI_2_DOMAIN dict, defaults to "DOI"
    :return: str, valid full URL of the specified Digital Object
    """
    return as_HTTPS_URL(DOI_2_DOMAIN[domain.upper()].format(doi), **kwargs)


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
    SCI_DIR_URL: str = "https://www.sciencedirect.com/science/article/abs/pii/"
    HEADERS: Dict[str, Dict[str, str]] = {
        "BIBTEX": {**HTTP_HEADERS, "accept": "application/x-bibtex"},
        "CROSSREF": {**HTTP_HEADERS, "referer": "api.crossref.org",
                     "accept": ("application/xml,application/xhtml+xml,"
                                "text/html,text/xml,*/*")},
        "ELSEVIER": {**HTTP_HEADERS, "X-ELS-APIKey": ELSA_API_KEY,
                     "Accept": ("text/html,application/xhtml+xml,"
                                "application/xml;q=0.9,image/avif,image/webp,"
                                "image/png,image/svg+xml,*/*;q=0.8"),
                     "DNT": "1",
                     "Connection": "keep-alive",
                     "Host": "www.sciencedirect.com",
                     # "Priority": "u=0, i"
                     "Referer": "https://linkinghub.elsevier.com/",  # "https://www.sciencedirect.com",
                     "Sec-Fetch-Dest": "document",
                     "Sec-Fetch-Mode": "navigate",
                     "Sec-Fetch-Site": "cross-site",
                     # "Sec-Fetch-User": "?1",
                     # "Upgrade-Insecure-Requests": "1",
                     }
        # "accept": ("application/xml,application/rdf+xml,application/json,text/xml,*/*")}
    }

    def __init__(self, fpath: Optional[str] = ABSTRACTS_FPATH,
                 verbosity: int = 0, debugging: bool = False) -> None:
        super().__init__(debugging=debugging)
        self.doi2resp = self.read_from_file(fpath)  # TODO Move elsewhere?
        self.elsa = Searcher(api_key=ELSA_API_KEY, verbosity=verbosity)
        scopus.init()

    def download(self, url: str | bytes,
                 headers: Dict[str, str] = dict(),
                 # allow_redirects: bool = True, timeout: int = 10,
                 # headers: Mapping[str, str] = {...},
                 url_params: Mapping[str, str] = {"mailto": EMAIL},
                 **kwargs: Any) -> requests.Response:
        # Default parameters for REST request
        # kwargs.setdefault("params", {"mailto": EMAIL})
        kwargs.setdefault("allow_redirects", True)
        kwargs.setdefault("timeout", 10)

        # Default headers for REST request; overwrite with any new ones
        # kwargs["headers"] = {**self.HEADERS, **kwargs.get("headers", dict())}  # {{**self.HEADERS, **kwargs.get("headers", dict())}
        return self.get(url, url_params, headers=headers, **kwargs)

    def download_bibtex(self, doi: str) -> BibDatabase:
        """
        Get citation
        :param doi: str, _description_
        :return: str, _description_
        """
        resp = self.download(doi2url(doi), headers=self.HEADERS["BIBTEX"])
        return bibtexparser.loads(resp.text.strip())

    def download_crossref(self, doi: str) -> dict | None:  # TODO ?
        return self.download(doi2url(doi, "crossref")).json()

    def download_from_elsevier(self, doi: str) -> dict | None:
        """
        _summary_ 
        :param doi: str, _description_
        :return: dict | None, _description_
        """
        abstract = None
        abstract_resp = self.download(doi2url(doi, "ELSEVIER"),  # self.ELSA_URL + doi,
                                      headers=self.HEADERS["ELSEVIER"],
                                      url_params={"view": "COMPLETE"})
        if abstract_resp.status_code == 200:
            tree = ElementTree.fromstring(abstract_resp.text)
        # try:
            # assert abstract_resp.status_code == 200
        # except (AssertionError, ElementTree.ParseError) as err:
            # self.debug_or_raise(err, locals())
            tree_iter = tree.iter()
            abstract = None
            el = next(tree_iter, None)
            while not abstract and el is not None:
                el = next(tree_iter, None)
                if el.tag == "description" or el.tag == "abstract":
                    abstract = el.text
        """
            if el.tag.rsplit('}', 1)[1] == 'openaccessTag':
                openaccess = el.text
        if openaccess != "0":  # and el.tag.endswith("url"):
            pdb.set_trace()
            scopus_URL = el.text
        scopus_resp = self.download(scopus_URL, headers=self.HEADERS["ELSEVIER"])
        """
        return abstract

    def download_redirecting_page(self, doi: str):
        abstract = None
        landing_resp = self.download(doi2url(doi))
        landing_URL = tldextract.extract(landing_resp.url)
        if landing_URL.domain == "elsevier" and \
                landing_URL.subdomain == "linkinghub":
            abstract = self.download_from_elsevier(doi)
        if not abstract:
            abstract = self.download_via_linkinghub(landing_resp.text)
        if not abstract:
            pdb.set_trace()
            print()
        return abstract

    def download_scopus(self, doi: str) -> dict | None:
        """
        _summary_ 
        :param doi: str, _description_
        """
        # HOW TO ACCESS SCOPUS:
        # https://pybliometrics.readthedocs.io/en/stable/access.html
        try:  # TODO Can only use "META" not "META_ABS" w/o InstToken?
            ab = scopus.AbstractRetrieval(doi, view="META_ABS")
            ab = getattr(ab, "description", getattr(ab, "abstract"))
        except ScopusException:
            ab = None
        except (AssertionError, ValueError) as err:
            self.debug_or_raise(err, locals())
        return ab

    def download_via_linkinghub(self, linkinghub_page_contents: str) -> str:
        linkinghub_soup = bs4.BeautifulSoup(
            linkinghub_page_contents.strip(), features="lxml")
        try:
            scidir_URL = urllib.parse.unquote(
                linkinghub_soup.input.attrs["value"])
        except AttributeError as err:
            self.debug_or_raise(err, locals())

        try:
            # Get PII from URL: everything after "/pii/" and before any params
            found_PII = re.findall(r"(?:\/pii\/)([^\?]*)", scidir_URL)
            assert found_PII
            pii = found_PII[0]

            # abstract = self.elsa.get_doc(AbsDoc, scp_id=pii)
            # final_URL = f"http://api.elsevier.com/content/article/pii/{pii}"
            final_URL = self.SCI_DIR_URL + pii
            pdb.set_trace()
            final_resp = self.download(
                final_URL, url_params=dict(), timeout=20)
            assert final_resp.status_code == 200  # TODO Why is the response still 403?
            abstract = parse_abstract_from_incomplete_XML_str(final_resp.text)
            return abstract
        except (AssertionError, requests.RequestException) as err:
            self.debug_or_raise(err, locals())

    def fetch(self, doi: str) -> Dict[str, str]:
        """
        _summary_ 
        :param doi: str, _description_
        """
        abstract = None
        resp_json = self.doi2resp.get(doi)
        """
        if not resp_json:
            abstract = self.download_scopus(doi)
            resp_json = self.download_crossref(doi)
        """
        try:
            if resp_json and "message" in resp_json \
                    and "abstract" in resp_json["message"]:
                abstract_txt = resp_json["message"]["abstract"].strip()
            else:
                abstract_txt = self.download_redirecting_page(doi).text
        except (AttributeError, KeyError, TypeError) as err:
            self.debug_or_raise(err, locals())
        try:
            # TODO add functionality to add newly downloaded abstracts to .JSON file
            abstract = parse_abstract_from_incomplete_XML_str(abstract_txt)
            assert abstract
            return abstract
        except (AssertionError, TypeError) as err:
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
