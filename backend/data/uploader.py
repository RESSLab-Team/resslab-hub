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

    upload_all(input_type, filenames)


if __name__ == "__main__":
    main()
