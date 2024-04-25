# qosst-alice - Alice module of the Quantum Open Software for Secure Transmissions.
# Copyright (C) 2021-2024 Yoann Piétri

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Commands for Alice tools submodule.
"""
import logging
import argparse
from pathlib import Path
import os

from qosst_core.logging import create_loggers

from qosst_alice import __version__
from qosst_alice.tools.calibrate_conversion_factor import calibration_conversion_factor
from qosst_alice.tools.charaterization_voa import characterize_voa

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_LOCATION = (
    Path(os.path.abspath(__file__)).parent.parent.parent / "config.toml"
)


def _create_main_parser() -> argparse.ArgumentParser:
    """Create the parser for the command line tool.

    Commands:
        conversion-factor

    Returns:
        argparse.ArgumentParser: the created parser.
    """
    parser = argparse.ArgumentParser(prog="qosst-alice-tools")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Level of verbosity. If none, nothing is printed to the console. -v will print warnings and errors, -vv will add info and -vvv will print all debug logs.",
    )

    subparsers = parser.add_subparsers()
    conversion_factor_parser = subparsers.add_parser(
        "conversion-factor", help="Compute conversion factor"
    )
    conversion_factor_parser.set_defaults(func=calibration_conversion_factor)
    conversion_factor_parser.add_argument(
        "--no-save",
        dest="save",
        action="store_false",
        help="Don't save the results.",
    )

    characterize_voa_parser = subparsers.add_parser(
        "characterize-voa", help="Characterize a VOA."
    )
    characterize_voa_parser.set_defaults(func=characterize_voa)
    characterize_voa_parser.add_argument(
        "--no-save",
        dest="save",
        action="store_false",
        help="Don't save the results.",
    )

    return parser


def main():
    """
    Main entrypoint of the command.
    """
    parser = _create_main_parser()

    args = parser.parse_args()

    # Set loggers
    create_loggers(args.verbose, None)

    if hasattr(args, "func"):
        args.func(args)
    else:
        print("No command specified. Run with -h|--help to see the possible commands.")


if __name__ == "__main__":
    main()
