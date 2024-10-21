#!/usr/bin/env python3

"""
Knower
Greg Conan: gregmconan@gmail.com
Created: 2024-07-26
Updated: 2024-09-30
"""
# Import standard libraries
import argparse
import os
import pdb
from typing import Dict

# Local custom imports
from knower.constants import DOI_EXAMPLES, EMAIL
from knower.AbstractFetcher import AbstractFetcher
from knower.elsa import run_elsapy_test
from knower.utilities import (
    SplitLogger, ShowTimeTaken
)
from knower.Validators import ArgParser


def main():
    # run_elsapy_test()
    _args = get_cli_args()
    SplitLogger.from_cli_args(_args)  # logger =

    abstracts = dict()
    fetcher = AbstractFetcher(debugging=_args["debugging"])
    for each_DOI in _args["doi"]:
        abstracts[each_DOI] = fetcher.fetch(each_DOI)
    pdb.set_trace()
    print("Done")


def get_cli_args() -> Dict[str, str]:
    parser = ArgParser()
    parser.add_argument(
        "-d", "-debug", "--debug", "--debugging",
        action="store_true",
        dest="debugging",
        help=("Include this flag to run in interactive debugging mode.")
    )
    parser.add_argument(
        "-doi", "--doi", "--doi-list",
        default=DOI_EXAMPLES,  # required=True,
        dest="doi",
        nargs="+",
        help=("The DOI (Digital Object Identifier) of every document to get.")
    )
    parser.add_argument(
        "-e", "-email", "--email", "--email-address",
        default=EMAIL,
        dest="email",
        help=("Valid email address to include in Crossref API REST requests.")
    )
    parser.add_new_out_dir_arg("log")
    parser.add_new_out_dir_arg("out")
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help=("Include this flag to print more info to stdout while running. "
              "Including the flag more times will print more information.")
    )
    return vars(parser.parse_args())


if __name__ == "__main__":
    with ShowTimeTaken(f"running {__file__}"):
        main()
