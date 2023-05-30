import argparse
import dataclasses

from . import utils as ut
from .config import Config, OutputProcessorConfig, AbbreviationConfig, OnlineUpdaterConfig  # noqa: F401


def __get_arg_parser() -> argparse.ArgumentParser:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", "-c", type=str, default=None, help="The config yaml file to use."
    )

    # Add all the parameters to the parser.
    cli_parameters = ut.get_all_cli_parameters(Config)
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


def get_config() -> Config:
    """Get the config based on the indicated config file and other arguments."""
    parser = __get_arg_parser()
    args = parser.parse_args()
    if args.config is not None:
        config = Config.from_yaml_file(args.config)
    else:
        config = Config()
    del args.config
    ut.update_object_with_dict(config, args.__dict__)

    return config
