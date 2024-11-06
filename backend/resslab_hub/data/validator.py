"""
Validator for csv data integrity
"""

from abc import ABC, abstractmethod
from csv import DictReader, reader
from datetime import datetime
from decimal import Decimal, InvalidOperation
from glob import iglob
from logging import error, info
from multiprocessing import get_context
from os import path
from typing import Any, List

from sqlalchemy import Boolean, Date, Float, Integer, Numeric, String, create_engine
from sqlalchemy.orm import Session

from resslab_hub.data.common import get_abs_path, get_file_encoding, is_empty_row
from resslab_hub.data.uploader import Type, get_args_all, get_safe_cpu_count
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.column import ColumnEntity
from resslab_hub.models.database.connection import Connection
from resslab_hub.models.database.hss_column import HSSColumn
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.utils.database import url

engine = create_engine(url, echo=False)


class ValidationError:
    def __init__(self, row: int, column: str, value: Any, message: str):
        self.row = row
        self.column = column
        self.value = value
        self.message = message

    def __str__(self):
        return f"Row {self.row}: {self.column}='{self.value}' - {self.message}"


class ValidationResult:
    def __init__(self, filename: str):
        self.filename = filename
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def add_error(self, row: int, column: str, value: Any, message: str):
        self.errors.append(ValidationError(row, column, value, message))

    def add_warning(self, row: int, column: str, value: Any, message: str):
        self.warnings.append(ValidationError(row, column, value, message))

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def __str__(self):
        result = [f"Validation results for {self.filename}:"]
        if self.errors:
            result.append("\nErrors:")
            result.extend(f"  - {error}" for error in self.errors)
        if self.warnings:
            result.append("\nWarnings:")
            result.extend(f"  - {warning}" for warning in self.warnings)
        if not self.errors and not self.warnings:
            result.append("✓ All checks passed")
        return "\n".join(result)


class Validator(ABC):
    """
    Abstract class for all validators
    """

    @abstractmethod
    def validate_one(self, file_path: str) -> ValidationResult:
        """
        Validate one file
        """


class TableValidator(Validator):
    """
    Validator for table data (csv files with headers matching table columns)
    """

    def __init__(self, base_model: Any, id_column_key: str = "id"):
        self.base_model = base_model
        self.id_column_key = id_column_key

    def validate_one(self, file_path: str) -> ValidationResult:
        file_path = get_abs_path(file_path)
        result = ValidationResult(path.basename(file_path))

        try:
            encoding = get_file_encoding(file_path)
            with open(file_path, encoding=encoding) as file:
                csv_reader = reader(file, strict=True)
                headers = next(csv_reader)

                # Validate headers
                expected_columns = {col.key for col in self.base_model.__table__.c}
                missing_columns = expected_columns - set(headers)
                if missing_columns:
                    result.add_error(
                        0,
                        "headers",
                        headers,
                        f"Missing required columns" f": {', '.join(missing_columns)}",
                    )

                # Validate rows
                for row_num, row in enumerate(csv_reader, start=1):
                    if is_empty_row(row):
                        result.add_warning(row_num, "row", row, "Empty row detected")
                        continue

                    for col_idx, value in enumerate(row):
                        if col_idx >= len(headers):
                            break

                        column_name = headers[col_idx]
                        if column_name not in expected_columns:
                            continue

                        column = self.base_model.__table__.c[column_name]
                        self._validate_field(result, row_num, column, value)

        except Exception as e:
            result.add_error(0, "file", file_path, f"Failed to process file: {str(e)}")

        return result

    def _validate_field(
        self, result: ValidationResult, row: int, column: Any, value: str
    ):
        # cf analyzer.py for column type determination and reference for now
        try:
            if value.upper() in ("NA", "NR"):
                if not column.nullable:
                    result.add_error(row, column.key, value, "Field cannot be null")
                return
            if isinstance(column.type, Boolean):
                if value.lower() not in ("yes", "no"):
                    result.add_error(row, column.key, value, "Must be 'yes' or 'no'")
            elif isinstance(column.type, Integer):
                try:
                    int(Decimal(value))
                except (InvalidOperation, ValueError):
                    result.add_error(row, column.key, value, "Must be an integer")
            elif isinstance(column.type, (Float, Numeric)):
                try:
                    Decimal(value)
                except InvalidOperation:
                    result.add_error(row, column.key, value, "Must be a number")
            elif isinstance(column.type, String):
                try:
                    str(value)
                except Exception:
                    result.add_error(row, column.key, value, "Must be a string")
            elif isinstance(column.type, Date):
                try:
                    datetime.strptime(value, "%d.%m.%y")
                except ValueError:
                    try:
                        datetime.strptime(value, "%d.%m.%Y")
                    except ValueError:
                        result.add_error(
                            row,
                            column.key,
                            value,
                            "Invalid date format: Expected format:"
                            " DD.MM.YY or DD.MM.YYYY",
                        )

        except Exception as e:
            result.add_error(row, column.key, value, f"Validation error: {str(e)}")


class CsvFileValidator(Validator):
    """
    Validator for CSV files with specific column requirements
    """

    def __init__(
        self,
        base_model: Any,
        required_columns: List[str],
        foreign_key_field: str,
    ) -> None:
        self.base_model = base_model
        self.required_columns = required_columns
        self.foreign_key_field = foreign_key_field

    def validate_one(self, file_path: str) -> ValidationResult:
        file_path = get_abs_path(file_path)
        result = ValidationResult(path.basename(file_path))

        try:
            filename = path.splitext(path.basename(file_path))[0]
            encoding = get_file_encoding(file_path)

            with open(file_path, encoding=encoding) as file:
                csv_reader = DictReader(file, strict=True)

                # Validate headers
                missing_columns = set(self.required_columns) - set(
                    csv_reader.fieldnames or []
                )
                if missing_columns:
                    result.add_error(
                        0,
                        "headers",
                        csv_reader.fieldnames,
                        f"Missing required columns" f": {', '.join(missing_columns)}",
                    )
                    return result

                # Validate rows and foreign key
                with Session(engine) as session:
                    # Check if foreign key exists
                    stmt = (
                        f"SELECT 1 FROM {self.base_model.__tablename__} "
                        f"WHERE {self.foreign_key_field} = :id"
                    )
                    exists = session.execute(stmt, {"id": filename}).first() is not None

                    if not exists:
                        result.add_error(
                            0,
                            self.foreign_key_field,
                            filename,
                            f"Foreign key '{filename}' does not exist in "
                            f"parent table",
                        )

                    # Validate each row
                    for row_num, row in enumerate(csv_reader, start=1):
                        for col_name in self.required_columns:
                            value = row.get(col_name)
                            if value is None or value.strip() == "":
                                result.add_error(
                                    row_num, col_name, value, "Required field is empty"
                                )
                            elif (
                                "moment" in col_name.lower()
                                or "force" in col_name.lower()
                            ):
                                try:
                                    Decimal(value)
                                except InvalidOperation:
                                    result.add_error(
                                        row_num, col_name, value, "Must be a number"
                                    )

        except Exception as e:
            result.add_error(0, "file", file_path, f"Failed to process file: {str(e)}")

        return result


def validate_one(input_type: Type, filename: str) -> ValidationResult:
    """
    Validate a single file based on its type
    """
    info(f"Validating {filename} as {input_type}")

    match input_type:
        case Type.BRACE:
            validator = TableValidator(Brace)
        case Type.COLUMN:
            validator = TableValidator(ColumnEntity)
        case Type.CONNECTION:
            validator = TableValidator(Connection)
        case Type.MATERIAL:
            validator = TableValidator(Material)
        case Type.RESIDUAL_STRESS:
            validator = TableValidator(ResidualStress)
        case Type.HSS_COLUMN:
            validator = TableValidator(HSSColumn)
        case Type.BRACE_DISPLACEMENT:
            validator = CsvFileValidator(
                Brace,
                ["Displacement [mm]", "Force [kN]"],
                "brace_id",
            )
        case Type.COLUMN_AXIAL_SHORTENING:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Axial Shortening [mm]"],
                "column_id",
            )
        case Type.COLUMN_MOMENT_STRONG:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Moment [kN-mm]"],
                "column_id",
            )
        case Type.COLUMN_MOMENT_WEAK:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Moment [kN-mm]"],
                "column_id",
            )
        case Type.CONNECTION_BEAM:
            validator = CsvFileValidator(
                Connection, ["Chord Rotation [rads]", "Moment [kN-mm]"], "connection_id"
            )
        case Type.CONNECTION_BEAM_WEST:
            validator = CsvFileValidator(
                Connection,
                [
                    "Chrord Rotation, θ [rads]",
                    "Moment [kN-mm]",
                ],
                "connection_id",
            )
        case Type.CONNECTION_GLOBAL:
            validator = CsvFileValidator(
                Connection,
                [
                    "Total story drift angle (rad)",
                    "Force in the actuator (kN)",
                ],
                "connection_id",
            )
        case Type.CONNECTION_GLOBAL_WEST:
            validator = CsvFileValidator(
                Connection,
                [
                    "Total story drift angle (rad)",
                    "Force in the actuator (kN)",
                ],
                "connection_id",
            )
        case Type.CONNECTION_PANEL_ZONE:
            validator = CsvFileValidator(
                Connection,
                [
                    "panel zone shear distortion (rad)",
                    "panel zone shear force (kN)",
                ],
                "connection_id",
            )
        case Type.MATERIAL_STRESS_STRAIN:
            validator = CsvFileValidator(
                Material,
                ["Sigma_true", "e_true"],
                "material_id",
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F1:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "residual_stress_id",
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F2:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "residual_stress_id",
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_W1:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "residual_stress_id",
            )
        case Type.RESIDUAL_STRESS_QP_COEFFICIENT:
            validator = CsvFileValidator(
                ResidualStress,
                ["qp_coefficient"],
                "residual_stress_id",
            )
        case Type.HSS_COLUMN_MOMENT_ROTATION:
            validator = CsvFileValidator(
                HSSColumn,
                ["rotation (rad)", "moment (kN.m)"],
                "hss_column_id",
            )
        case _:
            raise NotImplementedError(f"Unknown type {input_type}")

    return validator.validate_one(filename)


def validate_all(
    input_type: Type, filenames: List[str], cpu=None
) -> List[ValidationResult]:
    """
    Validate all files in parallel
    """
    if cpu is None:
        cpu = get_safe_cpu_count()

    info(f"Number of CPUs available: {cpu}")

    wildcard_args = [
        arg for filename in filenames for arg in get_args_all(input_type, filename)
    ]
    args = [(arg[0], filename) for arg in wildcard_args for filename in iglob(arg[1])]

    with get_context("spawn").Pool(cpu) as pool:
        results = pool.starmap(validate_one, args)

    # Log results
    for result in results:
        if result.is_valid():
            info(str(result))
        else:
            error(str(result))

    return results
