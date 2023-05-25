import argparse
import dataclasses
import os
from typing import Any

import yaml


@dataclasses.dataclass
class Abbreviation:
    """A class representing a conference abbreviation."""
    abbreviation: str
    full_names: list[str]


class Config:
    """A config object that can be accessed like a dictionary or an object."""
    def __init__(self, key_value_pairs: dict[str, Any]):
        self.__dict__ = key_value_pairs

    def __getitem__(self, item: str):
        return self.__dict__[item]

    def __setitem__(self, key: str, value) -> None:
        self.__dict__[key] = value


def __parse_abbreviation(raw_value: str) -> Abbreviation:
    # TODO: Implement this.
    pass


def __get_default_abbreviations():
    # TODO: Implement this.
    return []


def __get_arg_parser() -> argparse.ArgumentParser:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", type=str, default=None,
                        help="The config yaml file to use.")
    parser.add_argument("--model", "-m", type=str, default="maui",
                        help="The model to use.")
    parser.add_argument("-i", "--input", type=str, required=True,
                        help="The input bib file.")
    parser.add_argument(
        "-o", "--output", default="same", type=str, required=True,
        help="The output bib file."
    )
    filepath = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument(
        "-l",
        "--bibliographies",
        default=os.path.join(filepath, "bibliographies.txt"),
        type=str,
        help="The list of candidate bibliography files.",
    )
    parser.add_argument(
        "-a",
        "--abbreviations",
        default=__get_default_abbreviations(),
        type=__parse_abbreviation,
        nargs="+",
        help="The list of conference abbreviation data.",
    )
    parser.add_argument(
        "-d",
        "--deduplicate",
        default=True,
        type=bool,
        help="True to remove entries with duplicate keys.",
    )
    parser.add_argument(
        "-s",
        "--shorten",
        default=False,
        type=bool,
        help="True to shorten the conference names.",
    )
    parser.add_argument(
        "-r",
        "--remove",
        default="",
        type=str,
        help="A comma-seperated list of values you want to remove, "
             "such as '--remove url,biburl,address,publisher'.",
    )
    parser.add_argument(
        "-st",
        "--sort",
        default=False,
        type=bool,
        help="True to sort the output BibTeX entries alphabetically by ID",
    )
    parser.add_argument(
        "-ol",
        "--online",
        action="store_true",
        help="True to use online resources to look for missing BibTeX "
             "entries in a semi-automated way.",
    )
    return parser


def get_config() -> Config:
    """Get the config based on the indicated config file and other arguments."""
    parser = __get_arg_parser()
    args = parser.parse_args()
    if args.config is not None:
        config = Config(yaml.safe_load(open(args.config)))
        config = parser.parse_args(namespace=config)
    else:
        config = Config(args.__dict__)

    return config
