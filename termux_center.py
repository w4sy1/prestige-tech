"""Jedno wejście CLI dla Termux Setup i Termux Toolkit."""

import argparse
import json
import sys

from prestige_core import termux_setup, termux_toolkit


def build():
    parser = argparse.ArgumentParser(description="PRESTIGE TECH — Termux Center")
    subcommands = parser.add_subparsers(dest="area", required=True)
    setup = subcommands.add_parser("setup", help="Plan, instalacja i cofnięcie konfiguracji")
    setup.add_argument("--profile", choices=termux_setup.PROFILES, default="minimal")
    setup.add_argument("--apply", action="store_true")
    setup.add_argument("--rollback")
    setup.add_argument("--git-name")
    setup.add_argument("--git-email")
    setup.add_argument("--ssh-client", action="store_true")
    toolkit = subcommands.add_parser("toolkit", help="Osiem kategorii diagnostycznych")
    toolkit.set_defaults(menu=False)
    toolkit.add_argument("category", choices=termux_toolkit.CATEGORIES)
    toolkit.add_argument("--operation")
    toolkit.add_argument("--root", default=".")
    toolkit.add_argument("--target")
    toolkit.add_argument("--file")
    toolkit.add_argument("--archive")
    toolkit.add_argument("--apply", action="store_true")
    return parser


def main(argv=None):
    args = build().parse_args(argv)
    try:
        result = (termux_setup.handle(args) if args.area == "setup"
                  else termux_toolkit.handle(args))
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"Błąd: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
