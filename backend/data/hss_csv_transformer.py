import argparse
import csv
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Union

from resslab_hub.data.common import CSV_READ_MODE, UTF8_ENCODING


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

    mappings = [
        Mapping("id", lambda item: item["section"]),
        Mapping(
            "h",
            lambda item: from_number(Decimal(item["h"])),
        ),
        Mapping("b", lambda item: from_number(Decimal(item["b"]))),
        Mapping("t", lambda item: from_number(Decimal(item["t"]))),
        Mapping("ro", lambda item: from_number(Decimal(item["r_o"]))),
        Mapping("ro", lambda item: from_number(Decimal(item["r_o"]))),
        Mapping("ri", lambda item: from_number(Decimal(item["r_i"]))),
        Mapping("iy", lambda item: from_number(Decimal(item["i_y"]))),
        Mapping("ry", lambda item: from_number(Decimal(item["r_y"]))),
        Mapping("sy", lambda item: from_number(Decimal(item["s_y"]))),
        Mapping("zy", lambda item: from_number(Decimal(item["z_y"]))),
        Mapping("iz", lambda item: from_number(Decimal(item["i_z"]))),
        Mapping("rz", lambda item: from_number(Decimal(item["r_z"]))),
        Mapping("sz", lambda item: from_number(Decimal(item["s_z"]))),
    ]

    if source == Source.AISC:
        mappings = mappings + [
            Mapping("zz", lambda item: from_number(Decimal(item["z_z"]))),
        ]
    elif source == Source.EUROPEAN:
        # Similar to American but without INCH conversion
        mappings = mappings + [
            Mapping("zz", lambda item: from_number(Decimal(item["w_z"]))),
        ]
    elif source == Source.JAPANESE:
        mappings = mappings + [
            Mapping("zz", lambda item: from_number(Decimal(item["z_z"]))),
        ]

    transform(input, output, mappings)


if __name__ == "__main__":
    main()
