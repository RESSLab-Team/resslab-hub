import argparse
import csv
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Union

from resslab_hub.data.common import CSV_READ_MODE, UTF8_ENCODING

INCH = Decimal(25.4)


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
        with open(input_path, CSV_READ_MODE, encoding=UTF8_ENCODING) as input_file:
            reader = csv.DictReader(input_file, strict=True)
            for row in reader:
                if any(len(value) > 0 for value in row.values()):
                    writer.writerow([mapping.fn(row) for mapping in mappings])


def from_number(value: Union[Decimal, str]) -> Any:
    if isinstance(value, str):
        value = value.replace("'", "")
    return Decimal(value).normalize()


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
            Mapping("bf", lambda item: from_number(Decimal(item["b_f"]) * INCH)),
            Mapping(
                "h",
                lambda item: from_number(
                    (Decimal(item["d"]) - 2 * Decimal(item["k_des"])) * INCH
                ),
            ),
            Mapping("tf", lambda item: from_number(Decimal(item["t_f"]) * INCH)),
            Mapping("tw", lambda item: from_number(Decimal(item["t_w"]) * INCH)),
            Mapping(
                "ix", lambda item: from_number(Decimal(item["i_x"]) * pow(INCH, 4))
            ),
            Mapping(
                "zx", lambda item: from_number(Decimal(item["z_x"]) * pow(INCH, 3))
            ),
            Mapping("ry", lambda item: from_number(Decimal(item["r_y"]) * INCH)),
            Mapping("d", lambda item: from_number(Decimal(item["d"]) * INCH)),
            Mapping("a", lambda item: from_number(Decimal(item["a"]) * INCH)),
            Mapping("iy", lambda item: from_number(Decimal(item["i_y"]) * INCH)),
        ]
    elif source == Source.EUROPEAN:
        # Similar to American but without INCH conversion
        mappings = [
            Mapping("id", lambda item: item["section"]),
            Mapping("bf", lambda item: from_number(Decimal(item["b_f"]))),
            Mapping(
                "h",
                lambda item: from_number(
                    (Decimal(item["d"]) - 2 * Decimal(item["k_des"]))
                ),
            ),
            Mapping("tf", lambda item: from_number(Decimal(item["t_f"]))),
            Mapping("tw", lambda item: from_number(Decimal(item["t_w"]))),
            Mapping("ix", lambda item: from_number(Decimal(item["i_x"]))),
            Mapping("zx", lambda item: from_number(Decimal(item["z_x"]))),
            Mapping("ry", lambda item: from_number(Decimal(item["r_y"]))),
            Mapping("d", lambda item: from_number(Decimal(item["d"]))),
            Mapping("a", lambda item: from_number(Decimal(item["a"]))),
            Mapping("iy", lambda item: from_number(Decimal(item["i_y"]))),
        ]
    elif source == Source.JAPANESE:
        mappings = [
            Mapping("id", lambda item: item["cross_section"]),
            Mapping("bf", lambda item: from_number(item["b"])),
            Mapping(
                "h",
                lambda item: from_number(
                    Decimal(item["d"])
                    - 2 * Decimal(item["t_capital"])
                    - 2 * Decimal(item["r"]),
                ),
            ),
            Mapping("tf", lambda item: from_number(item["t_capital"])),
            Mapping("tw", lambda item: from_number(item["t"])),
            Mapping("ix", lambda item: from_number(item["i_x"].replace("'", ""))),
            Mapping("zx", lambda item: from_number(item["z_x"].replace("'", ""))),
            Mapping("ry", lambda item: from_number(item["r_y"])),
            Mapping("d", lambda item: from_number(item["d"])),
            Mapping("a", lambda item: from_number(item["a"])),
            Mapping("iy", lambda item: from_number(item["i_y"])),
        ]

    transform(input, output, mappings)


if __name__ == "__main__":
    main()
