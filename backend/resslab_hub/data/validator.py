"""
Validator for csv data integrity
"""

import traceback
from abc import ABC, abstractmethod
from csv import DictReader, reader
from datetime import datetime
from decimal import Decimal, InvalidOperation
from glob import iglob
from logging import debug, error, getLogger, info
from multiprocessing import get_context
from os import path
from typing import Any, List

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Float,
    Integer,
    Numeric,
    SmallInteger,
    String,
    create_engine,
    text,
)
from sqlalchemy.orm import Session

from resslab_hub.data.common import get_abs_path, get_file_encoding, is_empty_row
from resslab_hub.data.uploader import (
    Type,
    get_args_all,
    get_safe_cpu_count,
    initializer,
)
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.column import ColumnEntity
from resslab_hub.models.database.connection import Connection
from resslab_hub.models.database.hss_column import HSSColumn
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.utils.database import url

engine = create_engine(url, echo=False)

DecimalFloat = Float(asdecimal=True)


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
        self.error_count: Integer = 0
        self.warnings: List[ValidationError] = []

    def add_error(self, row: int, column: str, value: Any, message: str):
        self.errors.append(ValidationError(row, column, value, message))
        self.error_count += 1

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

                debug(f"Validating headers for {path.basename(file_path)}")
                # Validate headers
                expected_columns = {col.key for col in self.base_model.__table__.c}

                debug(f"Expected columns: {expected_columns}")
                debug(f"Found columns: {headers}")

                missing_columns = expected_columns - set(headers)
                unexpected_columns = set(headers) - expected_columns

                missing_columns = expected_columns - set(headers)
                if missing_columns:
                    error(f"Missing columns: {missing_columns}")
                    result.add_error(
                        0,
                        "headers",
                        headers,
                        f"Missing required columns: {', '.join(missing_columns)}",
                    )

                if unexpected_columns:
                    error(f"Unexpected columns: {unexpected_columns}")
                    result.add_warning(
                        0,
                        "headers",
                        headers,
                        f"Unexpected columns: {', '.join(unexpected_columns)}",
                    )

                # Validate rows
                for row_num, row in enumerate(csv_reader, start=1):
                    if is_empty_row(row):
                        result.add_warning(row_num, "row", row, "Empty row detected")
                        continue
                    # Add check for incomplete rows
                    if len(row) < len(headers):
                        result.add_error(
                            row_num,
                            "row",
                            row,
                            f"Row has fewer values ({len(row)})"
                            f"than headers ({len(headers)})",
                        )
                        continue

                    for col_idx, value in enumerate(row):
                        debug(f"Validating row {row_num}, column {col_idx}: {value}")
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
            # Check if value is a string and "NA" or "NR"
            if isinstance(value, str):
                if value.upper() == "NA":
                    if not column.nullable:
                        result.add_error(
                            row,
                            column.key,
                            value,
                            "Field cannot be null: column is not nullable",
                        )
                    # skip validation for 'NA' values
                    return
                elif value.upper() == "NR":
                    # Handle 'NR' as 'not reported' and skip validation
                    return

            # Validate based on column type
            if isinstance(column.type, String):
                try:
                    if value.upper() == "NA":
                        if not column.nullable:
                            result.add_error(
                                row,
                                column.key,
                                value,
                                "Field cannot be null: column is not nullable",
                            )
                    elif value.upper() == "NR":
                        # Handle 'NR' as 'not reported'
                        pass
                    # Try to convert value to string
                    str(value)
                except Exception:
                    result.add_error(row, column.key, value, "Must be a string")
            elif isinstance(column.type, Boolean):
                if value.lower() not in ("yes", "no"):
                    result.add_error(row, column.key, value, "Must be 'yes' or 'no'")
            elif isinstance(column.type, (SmallInteger, Integer, BigInteger)):
                try:
                    int(Decimal(value))
                except (InvalidOperation, ValueError):
                    result.add_error(row, column.key, value, "Must be an integer")
            elif isinstance(column.type, Float) and column.type.asdecimal:
                try:
                    # DecimalFloat is a Float with asdecimal=True
                    Decimal(value)
                except InvalidOperation:
                    result.add_error(
                        row, column.key, value, "Must be a number: Float as decimal"
                    )
            elif isinstance(column.type, Numeric):
                try:
                    float(value)
                except InvalidOperation:
                    result.add_error(
                        row, column.key, value, "Must be a number: Numeric float"
                    )

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
            elif value is None:
                if not column.nullable:
                    result.add_error(
                        row,
                        column.key,
                        value,
                        "Field cannot be null: column is not nullable",
                    )
                pass

        except Exception as e:
            print(
                f"Validation error missing type: {str(e)}"
                f"for column {column.key} with value {value}"
                f"and type {column.type}"
            )
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
        primary_csv_path: str = None,
    ) -> None:
        self.base_model = base_model
        self.required_columns = required_columns
        self.foreign_key_field = foreign_key_field
        self.primary_csv_path = primary_csv_path

    def _check_primary_csv(self, foreign_key: str) -> bool:
        """Check if the foreign key exists in the primary CSV being uploaded"""
        info(f"Checking primary CSV: {self.primary_csv_path}")
        if not self.primary_csv_path:
            return False

        try:
            encoding = get_file_encoding(get_abs_path(self.primary_csv_path))
            with open(get_abs_path(self.primary_csv_path), encoding=encoding) as file:
                csv_reader = DictReader(file)
                # return any(row.get("id") == foreign_key for row in csv_reader)
                for row in csv_reader:
                    if row.get("id") == foreign_key:
                        info(f"Match found for foreign key: {foreign_key}")
                        return True
                error(f"No match found for foreign key: {foreign_key}")
                return False
        except Exception as e:
            error(f"Error checking primary CSV: {str(e)}")
            return False

    def validate_one(self, file_path: str) -> ValidationResult:
        try:
            file_path = get_abs_path(file_path)
            relative_path = path.relpath(
                file_path, start=path.join(path.sep, *file_path.split(path.sep)[:7])
            )
            result = ValidationResult(path.basename(file_path))
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
                        f"Missing required columns: {', '.join(missing_columns)}",
                    )
                    return result

                # Validate rows and foreign key
                with Session(engine) as session:
                    # Check if foreign key exists
                    stmt = text(
                        f'SELECT 1 FROM "{self.base_model.__tablename__}" '
                        f"WHERE {self.foreign_key_field} = :id"
                    )
                    exists_in_db = (
                        session.execute(stmt, {"id": filename}).first() is not None
                    )
                    exists_in_primary = self._check_primary_csv(filename)

                    if self.primary_csv_path is None:
                        if not exists_in_db:
                            result.add_error(
                                0,
                                self.foreign_key_field,
                                filename,
                                f"Foreign key '{filename}' not found in "
                                f"database, no primary csv provided (cf "
                                f"{relative_path})",
                            )
                    elif not exists_in_primary:
                        result.add_error(
                            0,
                            self.foreign_key_field,
                            filename,
                            f"Foreign key '{filename}' not found "
                            f"in primary CSV (cf {relative_path})",
                        )

                    # Validate each row
                    for row_num, row in enumerate(csv_reader, start=1):
                        for col_name in self.required_columns:
                            # we don't validate against model definition because
                            # it may contain additional columns that are not required
                            # and it's always of type Numeric
                            value = row.get(col_name)
                            if value is None or value.strip() == "":
                                result.add_error(
                                    row_num, col_name, value, "Required field is empty"
                                )
                            else:
                                try:
                                    Decimal(value)
                                except InvalidOperation:
                                    result.add_error(
                                        row_num, col_name, value, "Must be a number"
                                    )
        except Exception as e:
            result.add_error(
                0, "file", relative_path, f"Failed to process file: {str(e)}"
            )

        return result


def validate_one_file(input_type: Type, filename: str) -> Validator:
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
                "id",  # id column in brace table
            )
        case Type.COLUMN_AXIAL_SHORTENING:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Axial Shortening [mm]"],
                "id",
            )
        case Type.COLUMN_MOMENT_STRONG:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Moment [kN-mm]"],
                "id",
            )
        case Type.COLUMN_MOMENT_WEAK:
            validator = CsvFileValidator(
                ColumnEntity,
                ["Chord Rotation [rads]", "Moment [kN-mm]"],
                "id",
            )
        case Type.CONNECTION_BEAM:
            validator = CsvFileValidator(
                Connection, ["Chord Rotation [rads]", "Moment [kN-mm]"], "id"
            )
        case Type.CONNECTION_BEAM_WEST:
            validator = CsvFileValidator(
                Connection,
                [
                    "Chord Rotation [rads]",
                    "Moment [kN-mm]",
                ],
                "id",
            )
        case Type.CONNECTION_GLOBAL:
            validator = CsvFileValidator(
                Connection,
                [
                    "Total story drift angle (rad)",
                    "Force in the actuator (kN)",
                ],
                "id",
            )
        case Type.CONNECTION_GLOBAL_WEST:
            validator = CsvFileValidator(
                Connection,
                [
                    "Total story drift angle (rad)",
                    "Force in the actuator (kN)",
                ],
                "id",
            )
        case Type.CONNECTION_PANEL_ZONE:
            validator = CsvFileValidator(
                Connection,
                [
                    "panel zone shear distortion (rad)",
                    "panel zone shear force (kN)",
                ],
                "id",
            )
        case Type.MATERIAL_STRESS_STRAIN:
            validator = CsvFileValidator(Material, ["Sigma_true", "e_true"], "id")
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F1:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "id",
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F2:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "id",
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_W1:
            validator = CsvFileValidator(
                ResidualStress,
                ["coordinate", "residual_stress"],
                "id",
            )
        case Type.RESIDUAL_STRESS_QP_COEFFICIENT:
            validator = CsvFileValidator(
                ResidualStress,
                ["qp_coefficient"],
                "id",
            )
        case Type.HSS_COLUMN_MOMENT_ROTATION:
            validator = CsvFileValidator(
                HSSColumn,
                ["rotation (rad)", "moment (kN.m)"],
                "id",
            )
        case _:
            raise NotImplementedError(f"Unknown type {input_type}")

    return validator


# Map subsidiary types to their primary types
PRIMARY_TYPE_MAP = {
    Type.BRACE_DISPLACEMENT: Type.BRACE,
    Type.COLUMN_AXIAL_SHORTENING: Type.COLUMN,
    Type.COLUMN_MOMENT_STRONG: Type.COLUMN,
    Type.COLUMN_MOMENT_WEAK: Type.COLUMN,
    Type.CONNECTION_BEAM: Type.CONNECTION,
    Type.CONNECTION_BEAM_WEST: Type.CONNECTION,
    Type.CONNECTION_GLOBAL: Type.CONNECTION,
    Type.CONNECTION_GLOBAL_WEST: Type.CONNECTION,
    Type.CONNECTION_PANEL_ZONE: Type.CONNECTION,
    Type.MATERIAL_STRESS_STRAIN: Type.MATERIAL,
    Type.RESIDUAL_STRESS_DISTRIBUTION_F1: Type.RESIDUAL_STRESS,
    Type.RESIDUAL_STRESS_DISTRIBUTION_F2: Type.RESIDUAL_STRESS,
    Type.RESIDUAL_STRESS_DISTRIBUTION_W1: Type.RESIDUAL_STRESS,
    Type.RESIDUAL_STRESS_QP_COEFFICIENT: Type.RESIDUAL_STRESS,
    Type.HSS_COLUMN_MOMENT_ROTATION: Type.HSS_COLUMN,
}


def validate_with_primary(
    input_type: Type, filename: str, primary_csv_paths: dict = None
) -> ValidationResult:
    """Helper function to create validator with appropriate primary CSV
    Args:
        input_type: The type of input file being validated
        filename: Path to the file being validated
    Returns:
        ValidationResult containing validation outcome
    """
    """Helper function to create validator with appropriate primary CSV"""
    try:
        validator = validate_one_file(input_type, filename)
        if isinstance(validator, CsvFileValidator):
            primary_type = PRIMARY_TYPE_MAP.get(input_type)
            if primary_type and primary_csv_paths:
                primary_csv_path = primary_csv_paths.get(primary_type)
                validator.primary_csv_path = primary_csv_path
        return validator.validate_one(filename)
    except Exception as e:
        error(f"Error in validate_with_primary: {str(e)}")
        error(f"Traceback: {traceback.format_exc()}")
        raise


def validate_all(
    input_type: Type, filenames: List[str], cpu=None
) -> List[ValidationResult]:
    """
    Validate all files in parallel
    """
    if cpu is None:
        cpu = get_safe_cpu_count()

    info(f"Number of CPUs available: {cpu}")

    # Get current logging configuration to pass to workers

    getLogger().setLevel("DEBUG")
    current_log_level = getLogger().level
    root_logger = getLogger()
    current_log_format = None
    if root_logger.handlers and hasattr(root_logger.handlers[0], "formatter"):
        if root_logger.handlers[0].formatter:
            current_log_format = root_logger.handlers[0].formatter._fmt

    wildcard_args = [
        arg for filename in filenames for arg in get_args_all(input_type, filename)
    ]
    args = [(arg[0], filename) for arg in wildcard_args for filename in iglob(arg[1])]

    # Split into primary and subsidiary types
    primary_types = [
        arg
        for arg in args
        if arg[0]
        in [
            Type.BRACE,
            Type.COLUMN,
            Type.CONNECTION,
            Type.MATERIAL,
            Type.RESIDUAL_STRESS,
            Type.HSS_COLUMN,
        ]
    ]
    subsidiary_types = [arg for arg in args if arg not in primary_types]
    info(
        f"Found {len(primary_types)} primary types"
        f"and {len(subsidiary_types)} subsidiary types"
    )

    # Create mapping of primary CSV paths
    primary_csv_paths = {
        Type.BRACE: next((f for t, f in primary_types if t == Type.BRACE), None),
        Type.COLUMN: next((f for t, f in primary_types if t == Type.COLUMN), None),
        Type.CONNECTION: next(
            (f for t, f in primary_types if t == Type.CONNECTION), None
        ),
        Type.MATERIAL: next((f for t, f in primary_types if t == Type.MATERIAL), None),
        Type.RESIDUAL_STRESS: next(
            (f for t, f in primary_types if t == Type.RESIDUAL_STRESS), None
        ),
        Type.HSS_COLUMN: next(
            (f for t, f in primary_types if t == Type.HSS_COLUMN), None
        ),
    }

    results = []

    # First validate primary files
    if primary_types:
        debug(f"Validating primary types: {[t.name for t, _ in primary_types]}")

        with get_context("spawn").Pool(
            cpu,
            initializer=initializer,
            initargs=(current_log_level, current_log_format),
        ) as pool:
            try:
                primary_results = pool.starmap(
                    validate_with_primary,
                    [(t, f, primary_csv_paths) for t, f in primary_types],
                )
                results.extend(primary_results)
            except Exception as e:
                error(f"Error in validate_all: {str(e)}")
                error(f"Traceback: {traceback.format_exc()}")
        # Check if all primary validations passed before proceeding
        # primary_errors = any(not result.is_valid() for result in primary_results)
        # if primary_errors:
        #     error("Primary file validation failed. Skipping subsidiary files.")
        #     return results

    # Then validate subsidiary files
    if subsidiary_types:
        debug(f"Validating subsidiary types: {[t.name for t, _ in subsidiary_types]}")

        with get_context("spawn").Pool(
            cpu,
            initializer=initializer,
            initargs=(current_log_level, current_log_format),
        ) as pool:
            subsidiary_results = pool.starmap(
                validate_with_primary,
                [(t, f, primary_csv_paths) for t, f in subsidiary_types],
            )
            results.extend(subsidiary_results)

    # Log results
    for result in results:
        if result.is_valid():
            info(str(result))
        else:
            error(str(result))

    return results
