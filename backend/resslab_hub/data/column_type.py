from enum import Enum


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
