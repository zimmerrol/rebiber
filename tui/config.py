import argparse
import dataclasses
import os
from typing import Any, Optional, Callable

import dataclass_wizard


_filepath = os.path.dirname(os.path.abspath(__file__))


def cli_parameter(
    short_name: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Optional[Callable[[], Any]] = dataclasses.MISSING,
    required: bool = False,
    help: Optional[str] = None,
):
    """A decorator to mark a field as configurable through a CLI parameter."""

    # If this is a required argument, we need to set a default value to anything,
    # otherwise, the class cannot be constructed by the YAML parser.
    return dataclasses.field(
        default=default if not required else None,
        default_factory=default_factory,
        repr=True,
        metadata=dict(
            is_cli_parameter=True,
            short_name=short_name,
            help=help,
            required=required,
            default=default,
            default_factory=default_factory,
        ),
    )


def __get_all_cli_parameters(cls, name_prefix="", short_prefix=""):
    """Get all the CLI parameters of a class."""
    cli_parameters = []
    fields = dataclasses.fields(cls)
    for field in fields:
        if field.metadata.get("is_cli_parameter", False):
            field_type = cls.__annotations__[field.name]
            if dataclasses.is_dataclass(field_type):
                cli_parameters += __get_all_cli_parameters(
                    field_type,
                    f"{name_prefix}{field.name}." if name_prefix else f"{field.name}.",
                    f"{short_prefix}{field.metadata['short_name']}."
                    if short_prefix
                    else f"{field.metadata['short_name']}.",
                )
            else:
                cli_parameters.append(
                    dict(
                        type=field_type,
                        name=name_prefix + field.name,
                        short_name=short_prefix + field.metadata["short_name"],
                        default=field.metadata["default"],
                        default_factory=field.metadata["default_factory"],
                        required=field.metadata["required"],
                        help=field.metadata["help"],
                    )
                )
    return cli_parameters


@dataclasses.dataclass
class OnlineUpdaterConfig:
    """Config for the manual reference updater."""

    enable: bool = cli_parameter(
        "e",
        default=True,
        help="True to enable the online/semi-automated " "reference updater.",
    )
    n_suggestions: int = cli_parameter(
        "n", default=3, help="Number of suggestions per service to show."
    )
    services: list[str] = cli_parameter(
        "s", default_factory=lambda: ["dblp", "crossref"], help="The services to use."
    )
    n_parallel_requests: int = cli_parameter(
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

    input: str = cli_parameter("i", required=True, help="The input bib file.")
    output: str = cli_parameter("o", required=True, help="The output bib file.")
    bibliography_folder: str = cli_parameter(
        "l",
        default=os.path.join(_filepath, "data"),
        help="Folder to load offline candidate bibliography files from.",
    )
    abbreviations: list[AbbreviationConfig] = cli_parameter(
        "a",
        default_factory=list,
        help="The list of conference abbreviation data.",
    )
    deduplicate: bool = cli_parameter(
        "d", default=True, help="True to remove entries with duplicate keys."
    )
    shorten: bool = cli_parameter(
        "s", default=False, help="True to shorten the conference names."
    )
    remove_fields: list[str] = cli_parameter(
        "r",
        default_factory=list,
        help="A list of fields to remove from the output entries.",
    )
    sort: bool = cli_parameter(
        "st",
        default=False,
        help="True to sort the output BibTeX entries " "alphabetically by ID.",
    )
    online_updater: OnlineUpdaterConfig = cli_parameter(
        "ol",
        default_factory=OnlineUpdaterConfig,
        help="Controls whether/how online resources are used to to look for missing "
        "BibTeX entries in a semi-automated way.",
    )


def __get_arg_parser() -> argparse.ArgumentParser:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", "-c", type=str, default=None, help="The config yaml file to use."
    )

    # Add all the parameters to the parser.
    cli_parameters = __get_all_cli_parameters(Config)
    for clip in cli_parameters:
        args = ["--" + clip["name"].replace("_", "-")]
        if clip["short_name"] is not None:
            # For now, argparse does not support multiple short names that start
            # identically. Therefore, we disable short names for now for nested
            # objects.
            # TODO: Revisit this.
            if "." not in clip["short_name"]:
                args.append("-" + clip["short_name"])
        if clip["default_factory"] is not dataclasses.MISSING:
            default = clip["default_factory"]()
        else:
            default = clip["default"]
        parser.add_argument(
            *args,
            type=clip["type"],
            default=default,
            help=clip["help"],
            required=clip["required"],
        )

    return parser


def __update_object_with_dict(obj, d):
    """Update an object with a dictionary considering nested values.

    Args:
        obj: The object to update.
        d: The dictionary to use to update the object.
    """
    if not dataclasses.is_dataclass(type(obj)):
        return

    # Update the top-level fields.
    keys = [k for k in d.keys() if "." not in k]
    for k in keys:
        field = [f for f in dataclasses.fields(type(obj)) if f.name == k][0]
        # Only update the field if it is a CLI parameter and the value is not
        # the default one.
        if field.metadata.get("is_cli_parameter", False):
            if field.metadata["default_factory"] is not dataclasses.MISSING:
                default = field.metadata["default_factory"]()
            else:
                default = field.metadata["default"]

            if d[k] != default:
                setattr(obj, k, d[k])

    # Update the nested fields.
    inner_keys = sorted([k for k in d.keys() if "." in k])
    previous_inner_key = None
    previous_inner_index = 0
    for i, k in enumerate(inner_keys):
        inner_key = k.split(".")[0]
        if previous_inner_key is None:
            previous_inner_key = inner_key
        if inner_key != previous_inner_key or i == len(inner_keys) - 1:
            previous_inner_key = inner_key
            inner_dict = {
                ".".join(l.split(".")[1:]): d[l]
                for l in inner_keys[previous_inner_index:i]
            }
            __update_object_with_dict(getattr(obj, inner_key), inner_dict)


def get_config() -> Config:
    """Get the config based on the indicated config file and other arguments."""
    parser = __get_arg_parser()
    args = parser.parse_args()
    if args.config is not None:
        config = Config.from_yaml_file(args.config)
    else:
        config = Config()
    del args.config
    __update_object_with_dict(config, args.__dict__)

    return config
