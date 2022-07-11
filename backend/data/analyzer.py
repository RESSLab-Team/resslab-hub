"""
CLI for uploading csv to database
"""
import csv
from argparse import ArgumentParser
from enum import Enum
from typing import List, Set

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from data.common import CSV_READ_MODE, UTF8_ENCODING, get_abs_path
from resslab_tools.utils.database import url

engine = create_engine(url, echo=False)
session = Session(engine)


class ColumnType(Enum):
    """
    https://docs.sqlalchemy.org/en/14/core/type_basics.html
    """

    BIG_INTEGER = "BigInteger"
    BOOLEAN = "Boolean"
    DECIMAL_FLOAT = "DecimalFloat"
    INTEGER = "Integer"
    NUMERIC = "Numeric"
    SMALL_INTEGER = "SmallInteger"
    STRING = "String"


class Column:
    __boolean_values = ["yes", "no"]

    def __init__(self, header: str) -> None:
        self.header: str = header
        self.values: Set[str] = set()

    def upper_values(self):
        return [value.upper() for value in self.values]

    def is_nullable(self) -> bool:
        return "NA" in self.upper_values()

    def get_type(self) -> ColumnType:
        non_null_values = [value for value in self.upper_values() if value != "NA"]
        if all([value.lower() in self.__boolean_values for value in non_null_values]):
            return ColumnType.BOOLEAN
        if all([value == "NR" or self.is_float(value) for value in non_null_values]):
            if "NR" in self.upper_values():
                return ColumnType.DECIMAL_FLOAT
            float_values = [float(value) for value in non_null_values]
            if all([value.is_integer() for value in float_values]):
                # https://www.postgresql.org/docs/current/datatype-numeric.html
                if all([-32768 < value and value < 32767 for value in float_values]):
                    return ColumnType.SMALL_INTEGER
                elif all(
                    [
                        -2147483648 < value and value < 2147483647
                        for value in float_values
                    ]
                ):
                    return ColumnType.INTEGER
                else:
                    return ColumnType.BIG_INTEGER
            else:
                return ColumnType.NUMERIC
        else:
            return ColumnType.STRING

    def get_declaration(self) -> str:
        args: List[str] = [self.get_type().value]
        if self.header == "id":
            args.append("primary_key=True")
        elif not self.is_nullable():
            args.append("nullable=False")
        return f"    {self.header} = Column({', '.join(args)})"

    @staticmethod
    def is_float(value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False


def analyze(filename: str):
    file_path = get_abs_path(filename)
    with open(file_path, CSV_READ_MODE, encoding=UTF8_ENCODING) as file:
        reader = csv.reader(file, strict=True)
        headers = next(reader)
        columns = [Column(header) for header in headers if header]
        for row in reader:
            for column, value in zip(columns, row):
                column.values.add(value)
        for column in columns:
            print(column.get_declaration())
        print()


def main():
    parser = ArgumentParser(description="csv files")
    parser.add_argument("filenames", nargs="+", help="data input file pattern")

    args = parser.parse_args()
    filenames: List[str] = args.filenames
    for filename in filenames:
        analyze(filename)


if __name__ == "__main__":
    main()
