"""Narzędzie właściciela: tworzenie kluczy i podpisywanie licencji PRO offline."""

import argparse
import getpass
from pathlib import Path

from prestige_core.offline_license import create_issuer_keys, issue_license


def main():
    parser = argparse.ArgumentParser(description="Prestige Tech — wydawanie licencji PRO")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init")
    initialize.add_argument("--private", required=True, type=Path,
                            help="Nowy prywatny klucz POZA repozytorium")
    initialize.add_argument("--public", required=True, type=Path,
                            help="Nowy publiczny klucz prestige_core/assets/pro-public.pem")
    issue = commands.add_parser("issue")
    issue.add_argument("--private", required=True, type=Path)
    issue.add_argument("--id", required=True)
    issue.add_argument("--expires", required=True, help="YYYY-MM-DD")
    issue.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    password = getpass.getpass("Hasło prywatnego klucza (nie wpisuj do czatu): ")
    if args.command == "init":
        result = create_issuer_keys(args.private, args.public, password)
        print("Utworzono publiczny klucz:", result["public_key"])
        print("Prywatny klucz trzymaj poza repozytorium i zachowaj bezpieczną kopię.")
    else:
        result = issue_license(args.private, password, args.id, args.expires, args.out)
        print("Utworzono licencję:", result["file"])


if __name__ == "__main__":
    main()
