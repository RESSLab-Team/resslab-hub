"""
CLI for uploading csv to database
"""

from argparse import ArgumentParser
from logging import DEBUG, INFO, basicConfig, debug
from typing import List

from resslab_hub.data.uploader import Type, engine, upload_all


def main():
    parser = ArgumentParser(description="Upload csv files to database")
    parser.add_argument("type", type=Type, choices=list(Type))
    parser.add_argument("filenames", nargs="+", help="data input file pattern")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--series-limit",
        type=int,
        default=None,
        help="upload at most N measurement files per series type; main tables, "
        "dictionaries and READMEs are always uploaded in full (used to build "
        "the lightweight per-worktree database template)",
    )

    args = parser.parse_args()
    input_type: Type = args.type
    filenames: List[str] = args.filenames

    log_level = DEBUG if args.debug else INFO
    basicConfig(
        level=log_level,
        format="[%(process)d] %(levelname)s:  %(message)s %(filename)s:%(lineno)d",
    )

    debug(f"Connecting to {engine.url}")
    debug(f"Log level set to {log_level}")

    upload_all(input_type, filenames, series_limit=args.series_limit)


if __name__ == "__main__":
    main()
