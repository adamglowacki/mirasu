"""Entry point: `mirasu <directory> [--recursive]`."""

import argparse
import sys
from pathlib import Path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mirasu")
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        help="Directory of photos/videos to triage. If omitted, Mirasu asks for one.",
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Scan the directory recursively"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    directory = None
    if args.directory is not None:
        directory = args.directory.resolve()
        if not directory.is_dir():
            print(f"Not a directory: {directory}", file=sys.stderr)
            return 1

    from .ui.app import MirasuApplication

    app = MirasuApplication(directory, recursive=args.recursive)
    return app.run([])


if __name__ == "__main__":
    sys.exit(main())
