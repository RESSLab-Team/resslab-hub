import argparse
import csv
from enum import Enum
from typing import Any, Callable, Dict, List, Union
from data.common import CSV_ENCODING, CSV_READ_MODE


INCH = 25.4


class Source(Enum):
    AISC = "aisc"
    EUROPEAN = "european"
    JAPANESE = "japanese"


class Mapping:
    def __init__(self, key: str, fn: Callable[[Dict[str, str]], Any]) -> None:
        self.key = key
        self.fn = fn


def transform(input_path: str, output_path: str, mappings: List[Mapping]) -> None:
    with open(output_path, "w", newline="") as output_file:
        writer = csv.writer(output_file, strict=True)
        writer.writerow([mapping.key for mapping in mappings])
        with open(input_path, CSV_READ_MODE, encoding=CSV_ENCODING) as input_file:
            reader = csv.DictReader(input_file, strict=True)
            for row in reader:
                if any(len(value) > 0 for value in row.values()):
                    writer.writerow([mapping.fn(row) for mapping in mappings])


def from_number(value: Union[float, str]) -> str:
    return f"{float(value):g}"


def main():
    parser = argparse.ArgumentParser(description="Transform CSV files")
    parser.add_argument("source", type=Source, choices=list(Source))
    parser.add_argument("input", help="input file location")
    parser.add_argument("output", help="output file location")

    args = parser.parse_args()
    source: Source = args.source
    input: str = args.input
    output: str = args.output

    mappings: List[Mapping] = []
    if source == Source.AISC:
        mappings = [
            Mapping("id", lambda item: item["section"]),
            Mapping("bf", lambda item: from_number(float(item["b_f"]) * INCH)),
            Mapping(
                "h",
                lambda item: from_number(
                    (float(item["d"]) - 2 * float(item["k_des"])) * INCH
                ),
            ),
            Mapping("tf", lambda item: from_number(float(item["t_f"]) * INCH)),
            Mapping("tw", lambda item: from_number(float(item["t_w"]) * INCH)),
            Mapping("ix", lambda item: from_number(float(item["i_x"]) * INCH)),
            Mapping("zx", lambda item: from_number(float(item["z_x"]) * INCH)),
            Mapping("ry", lambda item: from_number(float(item["r_y"]) * INCH)),
            Mapping("d", lambda item: from_number(float(item["d"]) * INCH)),
        ]
    elif source == Source.EUROPEAN:
        mappings = [
            Mapping("id", lambda item: item["cross_section"]),
            Mapping("bf", lambda item: from_number(item["b"])),
            Mapping(
                "h",
                lambda item: from_number(
                    float(item["h"]) - 2 * float(item["t_f"]) - 2 * float(item["r"]),
                ),
            ),
            Mapping("tf", lambda item: from_number(item["t_f"])),
            Mapping("tw", lambda item: from_number(item["t_w"])),
            Mapping("ix", lambda item: from_number(item["h"])),  # FIXME
            Mapping("zx", lambda item: from_number(item["h"])),  # FIXME
            Mapping("ry", lambda item: from_number(item["h"])),  # FIXME
            Mapping("d", lambda item: from_number(item["h"])),
        ]
    elif source == Source.JAPANESE:
        mappings = [
            Mapping("id", lambda item: item["cross_section"]),
            Mapping("bf", lambda item: from_number(item["b"])),
            Mapping(
                "h",
                lambda item: from_number(
                    float(item["d"])
                    - 2 * float(item["t_capital"])
                    - 2 * float(item["r"]),
                ),
            ),
            Mapping("tf", lambda item: from_number(item["t_capital"])),
            Mapping("tw", lambda item: from_number(item["t"])),
            Mapping("ix", lambda item: from_number(item["i_x"].replace("'", ""))),
            Mapping("zx", lambda item: from_number(item["z_x"].replace("'", ""))),
            Mapping("ry", lambda item: from_number(item["r_y"])),
            Mapping("d", lambda item: from_number(item["d"])),
        ]

    transform(input, output, mappings)


if __name__ == "__main__":
    main()
