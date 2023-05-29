import dataclasses
import os

import dataclass_wizard

from . import utils as ut

# The root directory of the app.
_basefolder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclasses.dataclass
class OnlineUpdaterConfig:
    """Config for the manual reference updater."""

    enable: bool = ut.cli_parameter(
        "e",
        default=True,
        help="True to enable the online/semi-automated " "reference updater.",
    )
    n_suggestions: int = ut.cli_parameter(
        "n", default=3, help="Number of suggestions per service to show."
    )
    services: list[str] = ut.cli_parameter(
        "s", default_factory=lambda: ["dblp", "crossref"], help="The services to use."
    )
    n_parallel_requests: int = ut.cli_parameter(
        "p",
        default=5,
        help="Number of parallel requests. Higher values may lead to "
        "to less buffering while updating references but this requires "
        "sufficiently high network bandwidth.",
    )


@dataclasses.dataclass
class AbbreviationConfig:
    """A class representing a conference abbreviation."""

    abbreviation: str
    full_names: list[str]


@dataclasses.dataclass
class Config(dataclass_wizard.YAMLWizard):
    """A config object that can be accessed like a dictionary or an object."""

    input: str = ut.cli_parameter("i", required=True, help="The input bib file.")
    output: str = ut.cli_parameter("o", required=True, help="The output bib file.")
    bibliography_folder: str = ut.cli_parameter(
        "l",
        default=os.path.join(_basefolder, "data"),
        help="Folder to load offline candidate bibliography files from.",
    )
    abbreviations: list[AbbreviationConfig] = ut.cli_parameter(
        "a",
        default_factory=list,
        help="The list of conference abbreviation data.",
    )
    deduplicate: bool = ut.cli_parameter(
        "d", default=True, help="True to remove entries with duplicate keys."
    )
    shorten: bool = ut.cli_parameter(
        "s", default=False, help="True to shorten the conference names."
    )
    remove_fields: list[str] = ut.cli_parameter(
        "r",
        default_factory=list,
        help="A list of fields to remove from the output entries.",
    )
    sort: bool = ut.cli_parameter(
        "st",
        default=False,
        help="True to sort the output BibTeX entries " "alphabetically by ID.",
    )
    online_updater: OnlineUpdaterConfig = ut.cli_parameter(
        "ol",
        default_factory=OnlineUpdaterConfig,
        help="Controls whether/how online resources are used to to look for missing "
        "BibTeX entries in a semi-automated way.",
    )
