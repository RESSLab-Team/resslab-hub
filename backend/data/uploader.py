"""
CLI for uploading csv to database
"""
from argparse import ArgumentParser
from logging import INFO, basicConfig, debug
from typing import List

from resslab_hub.data.uploader import Type, engine, upload_all


def main():
    parser = ArgumentParser(description="Upload csv files to database")
    parser.add_argument("type", type=Type, choices=list(Type))
    parser.add_argument("filenames", nargs="+", help="data input file pattern")

    args = parser.parse_args()
    input_type: Type = args.type
    filenames: List[str] = args.filenames

    debug(f"connecting to {engine.url}")

    upload_all(input_type, filenames)


if __name__ == "__main__":
    basicConfig(level=INFO)
    main()
