"""
CLI for uploading csv to database
"""

import traceback
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from collections import Counter
from csv import DictReader, reader
from datetime import datetime
from decimal import Decimal
from enum import Enum
from glob import iglob
from io import StringIO
from logging import DEBUG, INFO, basicConfig, debug, error, getLogger, info, warning
from multiprocessing import get_context
from os import path, sep
from typing import Any, Callable, List, Optional, Tuple

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    Integer,
    Numeric,
    String,
    create_engine,
    delete,
)
from sqlalchemy.orm import sessionmaker

from resslab_hub.data.common import get_abs_path, get_file_encoding, is_empty_row
from resslab_hub.data.count_flags import COUNT_FLAGS, recompute_count_flags
from resslab_hub.models.database.brace import Brace, BraceDisplacement
from resslab_hub.models.database.column import (
    ColumnAxialShortening,
    ColumnEntity,
    ColumnMomentStrong,
    ColumnMomentWeak,
)
from resslab_hub.models.database.connection import (
    Connection,
    ConnectionBeam,
    ConnectionBeamWest,
    ConnectionGlobal,
    ConnectionGlobalWest,
    ConnectionPanelZone,
)
from resslab_hub.models.database.dictionary import DatabaseReadme, DictionaryColumn
from resslab_hub.models.database.ductile_fracture import (
    DuctileFracture,
    DuctileFractureEpeqSimulation,
    DuctileFractureForceElongation,
    DuctileFractureForceElongationSimulation,
    DuctileFractureForceRadial,
    DuctileFractureForceRadialSimulation,
    DuctileFractureLodeSimulation,
    DuctileFractureTriaxSimulation,
)
from resslab_hub.models.database.eccentric_braced_frame import (
    EccentricBracedFrame,
    EccentricBracedFrameShearLinkAngle,
)
from resslab_hub.models.database.hss_column import HSSColumn, HSSColumnMomentRotation
from resslab_hub.models.database.material import Material, MaterialStressStrain
from resslab_hub.models.database.residual_stress import (
    ResidualStress,
    ResidualStressDistributionF1,
    ResidualStressDistributionF2,
    ResidualStressDistributionW1,
    ResidualStressQPCoefficient,
)
from resslab_hub.models.database.tensile_coupon import (
    TensileCoupon,
    TensileCouponStressStrain,
)
from resslab_hub.utils.database import url

engine = create_engine(url, echo=False)
Session = sessionmaker(engine)


# os sched_getaffinity(0) returns the number of CPUs the process CAN use
# instead of total number of CPUs with cpu_count()
# see https://docs.python.org/3/library/os.html#os.cpu_count


def _cgroup_cpu_quota():
    """CPUs the current cgroup is allowed, rounded up, or None if unrestricted.

    Inside a container sched_getaffinity()/cpu_count() still report every core
    on the *node* -- a CPU limit is a CFS bandwidth quota, not an affinity mask
    -- so they wildly overcount the CPUs a limited pod can actually use. Read
    the quota straight from the cgroup instead.
    """
    # cgroup v2
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            quota, period = f.read().split()
        if quota != "max" and int(period) > 0:
            return max(1, -(-int(quota) // int(period)))
    except (OSError, ValueError):
        pass
    # cgroup v1
    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as f:
            quota = int(f.read())
        with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as f:
            period = int(f.read())
        if quota > 0 and period > 0:
            return max(1, -(-quota // period))
    except (OSError, ValueError):
        pass
    return None


def get_safe_cpu_count() -> int:
    """Get a safe number of CPU count in a cross-platform way.

    Honours the container's CPU quota when present so a resource-capped pod does
    not spawn one worker per *node* core (which OOM-kills a memory-limited pod).
    """
    try:
        # Try Linux-specific sched_getaffinity first
        from os import sched_getaffinity

        available = len(sched_getaffinity(0))
    except (ImportError, AttributeError):
        # Fallback to cpu_count() for other platforms
        from multiprocessing import cpu_count

        available = cpu_count()

    quota = _cgroup_cpu_quota()
    if quota is not None:
        available = min(available, quota)

    return max(1, available - 1)


def initializer(log_level=None, log_format=None):
    """
    https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork
    """
    # Configure logging for this worker process
    import logging

    # Use provided log_level or default to INFO
    if log_level is None:
        log_level = logging.INFO
    if log_format is None:
        log_format = "[%(process)d] %(levelname)s: %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        force=True,  # Ensure configuration takes effect even if logging was initialized
    )

    engine.dispose(close=False)  # type: ignore


# Type enum defines the hierarchy of uploadable data:
# - ALL types: Process multiple related uploads (e.g., ALL_BRACE processes main
#   table + measurements)
# - Individual table types: For main entity tables (e.g., BRACE, COLUMN)
# - Measurement types: For time-series data linked to main tables (e.g.,
#   BRACE_DISPLACEMENT)


class Type(Enum):
    ALL = "all"  # Triggers upload of all data types
    DICTIONARY = "dictionary"  # A *_data_dictionary.csv file
    README = "readme"  # The README.md contributor guide of a database folder
    ALL_COLUMN = "all-columns"  # Main column table + related measurements
    ALL_BRACE = "all-braces"
    ALL_CONNECTION = "all-connections"
    ALL_MATERIAL = "all-material"
    ALL_RESIDUAL_STRESS = "all-residual-stresses"
    ALL_HSS_COLUMN = "all-hss-columns"
    ALL_ECCENTRIC_BRACED_FRAME = "all-eccentric-braced-frames"
    BRACE = "brace"
    BRACE_DISPLACEMENT = "brace-displacement"
    COLUMN = "column"
    COLUMN_AXIAL_SHORTENING = "column-axial-shortening"
    COLUMN_MOMENT_STRONG = "column-moment-strong"
    COLUMN_MOMENT_WEAK = "column-moment-weak"
    CONNECTION = "connection"
    CONNECTION_BEAM = "connection-beam"
    CONNECTION_BEAM_WEST = "connection-beam-west"
    CONNECTION_GLOBAL = "connection-global"
    CONNECTION_GLOBAL_WEST = "connection-global-west"
    CONNECTION_PANEL_ZONE = "connection-panel-zone"
    MATERIAL = "material"
    MATERIAL_STRESS_STRAIN = "material-stress-strain"
    RESIDUAL_STRESS = "residual-stress"
    RESIDUAL_STRESS_DISTRIBUTION_F1 = "residual-stress-distribution-f1"
    RESIDUAL_STRESS_DISTRIBUTION_F2 = "residual-stress-distribution-f2"
    RESIDUAL_STRESS_DISTRIBUTION_W1 = "residual-stress-distribution-w1"
    RESIDUAL_STRESS_QP_COEFFICIENT = "residual-stress-qp-coefficient"
    HSS_COLUMN = "hss-column"
    HSS_COLUMN_MOMENT_ROTATION = "hss-column-moment-rotation"
    ECCENTRIC_BRACED_FRAME = "eccentric-braced-frame"
    ECCENTRIC_BRACED_FRAME_SHEAR_LINK_ANGLE = "eccentric-braced-frame-shear-link-angle"
    ALL_TENSILE_COUPON = "all-tensile-coupons"
    TENSILE_COUPON = "tensile-coupon"
    TENSILE_COUPON_STRESS_STRAIN = "tensile-coupon-stress-strain"
    ALL_DUCTILE_FRACTURE = "all-ductile-fractures"
    DUCTILE_FRACTURE = "ductile-fracture"
    DUCTILE_FRACTURE_FORCE_ELONGATION = "ductile-fracture-force-elongation"
    DUCTILE_FRACTURE_FORCE_ELONGATION_SIMULATION = (
        "ductile-fracture-force-elongation-simulation"
    )
    DUCTILE_FRACTURE_FORCE_RADIAL = "ductile-fracture-force-radial"
    DUCTILE_FRACTURE_FORCE_RADIAL_SIMULATION = (
        "ductile-fracture-force-radial-simulation"
    )
    DUCTILE_FRACTURE_EPEQ_SIMULATION = "ductile-fracture-epeq-simulation"
    DUCTILE_FRACTURE_LODE_SIMULATION = "ductile-fracture-lode-simulation"
    DUCTILE_FRACTURE_TRIAX_SIMULATION = "ductile-fracture-triax-simulation"


# Main-table types: uploaded before everything else so the per-experiment
# measurement rows have their foreign-key targets in place.
PRIMARY_TYPES = frozenset(
    {
        Type.BRACE,
        Type.COLUMN,
        Type.CONNECTION,
        Type.MATERIAL,
        Type.RESIDUAL_STRESS,
        Type.HSS_COLUMN,
        Type.ECCENTRIC_BRACED_FRAME,
        Type.TENSILE_COUPON,
        Type.DUCTILE_FRACTURE,
    }
)

# Types never capped by upload_all's series_limit: the main tables plus the
# one-per-folder dictionary/README files (capping those per Type would keep a
# single component's dictionary and drop the other eight).
SERIES_EXEMPT_TYPES = PRIMARY_TYPES | {Type.DICTIONARY, Type.README}


# Abstract base class defining the upload interface
class Uploader(ABC):
    """
    Abstract class for all uploaders
    Four concrete implementations:
    - TableUploader: For main entity tables (1:1 mapping with DB schema)
    - CsvFileUploader: For measurement data (linked to parent records)
    - DictionaryUploader: For the *_data_dictionary.csv of a database
    - ReadmeUploader: For the README.md contributor guide of a database folder
    """

    @abstractmethod
    def upload_one(self, file_path: str) -> str:
        """
        Upload one file
        """


# Handles main entity tables where CSV headers match DB column names
class TableUploader(Uploader):
    """
    Uploader from csv to table (csv header and table column name should match)
    Process:
    1. Reads CSV with matching headers
    2. Validates and converts data types
    3. Creates DB model instances
    4. Handles updates and deletions
    """

    def __init__(self, base_model: Any, id_column_key: str = "id") -> None:
        """
        Initialize uploader for main entity tables
        - base_model: SQLAlchemy model defining table schema
        - id_column_key: Primary key column name (default 'id')
        """
        self.base_model = base_model
        self.id_column_key = id_column_key
        self.id_column = base_model.__dict__[id_column_key]

    def upload_one(self, file_path: str) -> str:
        """
        Process single CSV file for main entity table
        1. Reads CSV and matches headers to DB columns
        2. Tracks existing records for update/delete
        3. Converts data types (handles NA/NR values)
        4. Merges new/updated records
        5. Removes deleted records
        """
        file_path = get_abs_path(file_path)
        debug(f"Path to upload: {file_path}")
        try:
            encoding = get_file_encoding(file_path)
            with (
                open(file_path, encoding=encoding) as file,
                engine.connect() as connection,
                Session(bind=connection) as session,
            ):
                csv_reader = reader(file, strict=True)
                headers = next(csv_reader)
                id_index = headers.index(self.id_column_key)
                ids = []
                added_count, modified_count = 0, 0

                for i, header in enumerate(headers):
                    debug(f"Header {i}: '{header}'")

                existing_ids = {row[0] for row in session.query(self.id_column).all()}
                # derived flags have no CSV header; recomputed after the upload
                derived = COUNT_FLAGS.get(self.base_model, {})
                debug(
                    f"Opened file {path.basename(file_path)}, "
                    f"encoding: {encoding}, id_index: {id_index}"
                )
                # add new rows
                for i, row in enumerate(csv_reader):
                    debug(f"Row {i} length: {len(row)}")
                    if len(row) < len(headers):
                        debug(
                            f"  Warning: Row {i} has fewer elements ({len(row)}) than "
                            f"headers ({len(headers)})"
                        )
                    if is_empty_row(row):
                        warning("skip empty line")
                    else:
                        ids.append(row[id_index])
                        data = {
                            column.key: self.__get_value(column, headers, row)
                            for column in self.base_model.__table__.c
                            if column.key not in derived
                        }
                        if row[id_index] in existing_ids:
                            modified_count += 1
                        else:
                            added_count += 1
                        session.merge(self.base_model(**data))
                # remove outdated rows
                removed_ids = existing_ids - set(ids)
                if removed_ids:
                    session.execute(
                        delete(self.base_model).where(self.id_column.in_(removed_ids)),
                    )
                    warning(f"deleted {removed_ids}")
                session.commit()
                info("Session commited")
                return (
                    f"{path.basename(file_path)}: {added_count}++|"
                    f"{modified_count}**|{len(removed_ids)}--"
                )

        except Exception as e:
            error_traceback = traceback.format_exc()
            error_message = f"Skipping {file_path} due to error: {e}"
            error(error_message)
            debug(f"Full traceback: \n{error_traceback}")
            return f"{error_message} (see logs for details)"

    @staticmethod
    def __get_value(column: Column, headers: List[str], row: List[str]) -> Any:
        """
        Data type conversion and validation
        Handles:
        - NA/NR values (None/Not applicable)
        - Boolean conversions (yes/no)
        - Numeric types (Integer/Float/Decimal)
        - Date formatting
        - String values
        """
        index = headers.index(column.key or "")
        value = row[index]

        if value == "":
            if isinstance(column.type, String):
                return ""
            return None
        if value.upper() == "NA":
            if isinstance(column.type, String):
                return "Not applicable"
            return None
        if value.upper() == "NR":
            if isinstance(column.type, String):
                return "Not reported"
            return None
        if value.upper() == "NAN":
            if isinstance(column.type, String):
                return "Not a number"
            return None
        if isinstance(column.type, Boolean):
            if value.lower() == "yes":
                return True
            if value.lower() == "no":
                return False
            raise ValueError(f"unexpected {column.key}={value}")
        if isinstance(column.type, Integer):
            return int(Decimal(value))
        if isinstance(column.type, (Float, Numeric)):
            return Decimal(value)
        if isinstance(column.type, Date):
            try:
                return datetime.strptime(value, "%d.%m.%y").date()
            except Exception:
                try:
                    return datetime.strptime(value, "%d.%m.%Y").date()
                except Exception:
                    raise ValueError(
                        f"unexpected datetime.strptime {column.key}={value}"
                    )
        return str(value)


def _copy_encode(value: Any) -> str:
    """
    Encode one value for a ``COPY ... FROM STDIN`` text-format stream.

    ``None`` becomes the NULL marker (``\\N``); an empty string stays an empty
    field, so it still fails a numeric column exactly as the previous INSERT
    did -- keeping skip behaviour identical. Backslash and the field/record
    separators are escaped per the COPY text format.
    """
    if value is None:
        return r"\N"
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


# Handles measurement data that belongs to parent records
class CsvFileUploader(Uploader):
    """
    Uploader from csv to table
    Process:
    1. Extracts parent ID from filename
    2. Verifies parent record exists
    3. Validates measurement data format
    4. Creates measurement records linked via foreign keys
    5. Manages existing measurements (delete & replace)
    """

    def __init__(
        self,
        base_model: Any,
        get_delete: Callable[[str], delete],
        get_instance: Callable[[str, int, dict[str, str]], dict[str, Any]],
        filename_prefix="",
        filename_suffix="",
    ) -> None:
        """
        Initialize uploader for measurement data
        - base_model: SQLAlchemy model defining the measurement table schema
        - get_delete: Function to remove existing measurements
        - get_instance: Function returning a column->value mapping for one row
        - filename_prefix/suffix: For extracting parent ID from filename
        """
        self.base_model = base_model
        self.get_delete = get_delete
        self.get_instance = get_instance
        self.filename_prefix = filename_prefix
        self.filename_suffix = filename_suffix

    def upload_one(self, file_path: str) -> str:
        """
        Process single measurement CSV file
        1. Extracts parent ID from filename
        2. Deletes existing measurements for this parent
        3. Validates measurement data format
        4. Creates new records with foreign key to parent
        5. Handles transaction rollback on errors
        """
        file_path = get_abs_path(file_path)
        try:
            filename = self.__get_filename(file_path)
            id = filename.removeprefix(self.filename_prefix).removesuffix(
                self.filename_suffix
            )
            encoding = get_file_encoding(file_path)
            with (
                open(file_path, encoding=encoding) as file,
                engine.connect() as connection,
                Session(bind=connection) as session,
            ):
                reader = DictReader(file, strict=True)
                session.execute(self.get_delete(id))
                # The parent's rows are deleted and fully re-inserted, so there
                # is no merge/identity to resolve. Build plain column->value
                # mappings (no ORM objects) and stream them in with a single
                # COPY -- far cheaper than batched INSERTs.
                mappings = [
                    self.get_instance(id, index, value)
                    for index, value in enumerate(reader)
                ]
                try:
                    if mappings:
                        self.__copy(connection, mappings)
                    session.commit()
                    return path.basename(file_path)
                except Exception:
                    session.rollback()
                    raise
        except Exception as e:
            error_message = f"skiping {file_path} due to error {e}"
            error(error_message)
            return error_message

    def __copy(self, connection, mappings: List[dict]) -> None:
        """
        Bulk-load row mappings into the table with a single COPY ... FROM STDIN,
        running on the session's existing transaction so it commits/rolls back
        together with the preceding delete.
        """
        columns = list(mappings[0].keys())
        buffer = StringIO()
        for row in mappings:
            buffer.write("\t".join(_copy_encode(row[column]) for column in columns))
            buffer.write("\n")
        buffer.seek(0)
        column_list = ", ".join(f'"{column}"' for column in columns)
        table_name = self.base_model.__table__.name
        statement = f'COPY "{table_name}" ({column_list}) FROM STDIN'
        dbapi_connection = connection.connection.driver_connection
        with dbapi_connection.cursor() as cursor:
            cursor.copy_expert(statement, buffer)

    @staticmethod
    def __get_filename(file_path: str) -> str:
        """
        Extract filename for parent ID parsing
        Used by CsvFileUploader to link measurements to parent records
        """
        basename = path.basename(file_path)
        return path.splitext(basename)[0]


# Data-dictionary CSV basename -> frontend DatabaseId. The mapping lives here so
# the frontend consumes /dictionary keys as-is.
DICTIONARY_DATABASES = {
    "connections_data_dictionary.csv": "connections",
    "steel_columns_data_dictionary.csv": "columns",
    "steel_braces_data_dictionary.csv": "braces",
    "hss_columns_data_dictionary.csv": "hss",
    "steel_material_data_dictionary.csv": "cyclic",
    "residual_stresses_data_dictionary.csv": "residuals",
    "eccentric_braced_frames_data_dictionary.csv": "ebf",
    "tensile_coupons_data_dictionary.csv": "tensile",
    "ductile_fracture_data_dictionary.csv": "ductile-fracture",
}


class DictionaryUploader(Uploader):
    """
    Loads a ``*_data_dictionary.csv`` into the dictionary_column table.

    The dictionary CSVs don't fit TableUploader (they carry neither the
    database discriminator nor the row position), so rows are built here and the
    database's previous entries replaced wholesale.
    """

    def upload_one(self, file_path: str) -> str:
        file_path = get_abs_path(file_path)
        database = DICTIONARY_DATABASES.get(path.basename(file_path))
        if database is None:
            return f"Skipping unknown dictionary file {path.basename(file_path)}"

        rows = []
        with open(file_path, newline="", encoding="utf-8-sig") as file:
            for position, entry in enumerate(DictReader(file)):
                column_name = (entry.get("column_name") or "").strip()
                if not column_name:
                    continue
                rows.append(
                    DictionaryColumn(
                        database=database,
                        column_name=column_name,
                        position=position,
                        description=(entry.get("description") or "").strip(),
                        symbol=(entry.get("symbol") or "").strip(),
                        unit=(entry.get("unit") or "").strip(),
                        type=(entry.get("type") or "String").strip(),
                        example=(entry.get("example_value") or "").strip(),
                        nullable=(entry.get("nullable") or "").strip() == "True",
                        group=(entry.get("group") or "").strip(),
                    )
                )

        with Session() as session:
            session.execute(
                delete(DictionaryColumn).where(DictionaryColumn.database == database)
            )
            session.add_all(rows)
            session.commit()
        return f"{path.basename(file_path)}: {len(rows)} dictionary columns"


# Data-repo folder (relative to the archive root) -> frontend DatabaseId, for
# the README.md each folder carries.
README_DATABASES = {
    "braces": "braces",
    "columns": "columns",
    "connections": "connections",
    "hss_columns": "hss",
    "material/cyclic_coupons": "cyclic",
    "material/tensile_coupons": "tensile",
    "material/ductile_fracture": "ductile-fracture",
    "residual_stresses": "residuals",
    "eccentric_braced_frames": "ebf",
}


def readme_database(file_path: str) -> Optional[str]:
    """
    The DatabaseId a README.md belongs to, from the folder it sits in. The
    archive root is unknown here, so the deepest matching suffix wins
    (``.../material/cyclic_coupons/README.md`` -> ``cyclic``).
    """
    folder = path.dirname(path.abspath(file_path)).replace(sep, "/")
    for suffix, database in sorted(
        README_DATABASES.items(), key=lambda item: -len(item[0])
    ):
        if folder == suffix or folder.endswith("/" + suffix):
            return database
    return None


class ReadmeUploader(Uploader):
    """
    Stores a database folder's ``README.md`` verbatim so the frontend can
    render the contributor guide next to the data dictionary.
    """

    def upload_one(self, file_path: str) -> str:
        file_path = get_abs_path(file_path)
        database = readme_database(file_path)
        if database is None:
            return f"Skipping README in unknown folder {path.dirname(file_path)}"
        with open(file_path, encoding="utf-8-sig") as file:
            content = file.read()
        with Session() as session:
            session.merge(DatabaseReadme(database=database, content=content))
            session.commit()
        return f"{database}/README.md: {len(content)} characters"


def upload_one(input_type: Type, filename: str) -> str:
    """
    Handles individual file uploads based on type
    Process:
    1. Matches type to appropriate uploader
    2. Configures uploader with correct table/measurement mappings
    3. Returns upload status message

    For measurement data:
    - Defines foreign key relationships
    - Specifies CSV column mappings
    - Handles data type conversions
    """
    info(f"Upload one: {input_type}, {filename}")
    try:
        match input_type:
            case Type.DICTIONARY:
                uploader = DictionaryUploader()
            case Type.README:
                uploader = ReadmeUploader()
            case Type.BRACE:
                uploader = TableUploader(Brace)
            case Type.COLUMN:
                uploader = TableUploader(ColumnEntity)
            case Type.CONNECTION:
                uploader = TableUploader(Connection)
            case Type.MATERIAL:
                uploader = TableUploader(Material)
            case Type.RESIDUAL_STRESS:
                uploader = TableUploader(ResidualStress)
            case Type.HSS_COLUMN:
                uploader = TableUploader(HSSColumn)
            case Type.ECCENTRIC_BRACED_FRAME:
                uploader = TableUploader(EccentricBracedFrame)
            case Type.TENSILE_COUPON:
                uploader = TableUploader(TensileCoupon)
            case Type.TENSILE_COUPON_STRESS_STRAIN:
                uploader = CsvFileUploader(
                    TensileCouponStressStrain,
                    lambda id: delete(TensileCouponStressStrain).where(
                        TensileCouponStressStrain.tensile_coupon_id == id
                    ),
                    lambda id, index, value: dict(
                        tensile_coupon_id=id,
                        id=index,
                        stress=value.get("Stress_eng"),
                        strain=value.get("strain_eng"),
                    ),
                )
            case Type.ECCENTRIC_BRACED_FRAME_SHEAR_LINK_ANGLE:
                uploader = CsvFileUploader(
                    EccentricBracedFrameShearLinkAngle,
                    lambda id: delete(EccentricBracedFrameShearLinkAngle).where(
                        EccentricBracedFrameShearLinkAngle.eccentric_braced_frame_id
                        == id
                    ),
                    lambda id, index, value: dict(
                        eccentric_braced_frame_id=id,
                        id=index,
                        gamma_t=value.get("gamma_t"),
                        v=value.get("V"),
                    ),
                    filename_prefix="id",
                )
            case Type.BRACE_DISPLACEMENT:
                uploader = CsvFileUploader(
                    BraceDisplacement,
                    lambda id: delete(BraceDisplacement).where(
                        BraceDisplacement.brace_id == id
                    ),
                    lambda id, index, value: dict(
                        brace_id=id,
                        id=index,
                        displacement=value.get("Displacement [mm]"),
                        force=value.get("Force [kN]"),
                    ),
                )
            case Type.COLUMN_AXIAL_SHORTENING:
                uploader = CsvFileUploader(
                    ColumnAxialShortening,
                    lambda id: delete(ColumnAxialShortening).where(
                        ColumnAxialShortening.column_id == id
                    ),
                    lambda id, index, value: dict(
                        column_id=id,
                        id=index,
                        chord_rotation=value.get("Chord Rotation [rads]"),
                        axial_shortening=value.get("Axial Shortening [mm]"),
                    ),
                )
            case Type.COLUMN_MOMENT_STRONG:
                uploader = CsvFileUploader(
                    ColumnMomentStrong,
                    lambda id: delete(ColumnMomentStrong).where(
                        ColumnMomentStrong.column_id == id
                    ),
                    lambda id, index, value: dict(
                        column_id=id,
                        id=index,
                        chord_rotation=value.get("Chord Rotation [rads]"),
                        moment=value.get("Moment [kN-mm]"),
                    ),
                )
            case Type.COLUMN_MOMENT_WEAK:
                uploader = CsvFileUploader(
                    ColumnMomentWeak,
                    lambda id: delete(ColumnMomentWeak).where(
                        ColumnMomentWeak.column_id == id
                    ),
                    lambda id, index, value: dict(
                        column_id=id,
                        id=index,
                        chord_rotation=value.get("Chord Rotation [rads]"),
                        moment=value.get("Moment [kN-mm]"),
                    ),
                )
            case Type.CONNECTION_BEAM:
                uploader = CsvFileUploader(
                    ConnectionBeam,
                    lambda id: delete(ConnectionBeam).where(
                        ConnectionBeam.connection_id == id
                    ),
                    lambda id, index, value: dict(
                        connection_id=id,
                        id=index,
                        chord_rotation=value.get("Chord Rotation [rads]")
                        or value.get("Chrord Rotation, θ [rads]"),
                        moment=value.get("Moment [kN-mm]"),
                    ),
                )
            case Type.CONNECTION_BEAM_WEST:
                uploader = CsvFileUploader(
                    ConnectionBeamWest,
                    lambda id: delete(ConnectionBeamWest).where(
                        ConnectionBeamWest.connection_id == id
                    ),
                    lambda id, index, value: dict(
                        connection_id=id,
                        id=index,
                        chord_rotation=value.get("Chord Rotation [rads]")
                        or value.get("Chrord Rotation, θ [rads]"),
                        moment=value.get("Moment [kN-mm]"),
                    ),
                )
            case Type.CONNECTION_GLOBAL:
                uploader = CsvFileUploader(
                    ConnectionGlobal,
                    lambda id: delete(ConnectionGlobal).where(
                        ConnectionGlobal.connection_id == id
                    ),
                    lambda id, index, value: dict(
                        connection_id=id,
                        id=index,
                        story_drift_angle=value.get("Total story drift angle (rad)"),
                        actuator_force=value.get("Force in the actuator (kN)"),
                    ),
                )
            case Type.CONNECTION_GLOBAL_WEST:
                uploader = CsvFileUploader(
                    ConnectionGlobalWest,
                    lambda id: delete(ConnectionGlobalWest).where(
                        ConnectionGlobalWest.connection_id == id
                    ),
                    lambda id, index, value: dict(
                        connection_id=id,
                        id=index,
                        story_drift_angle=value.get("Total story drift angle (rad)"),
                        actuator_force=value.get("Force in the actuator (kN)"),
                    ),
                )
            case Type.CONNECTION_PANEL_ZONE:
                uploader = CsvFileUploader(
                    ConnectionPanelZone,
                    lambda id: delete(ConnectionPanelZone).where(
                        ConnectionPanelZone.connection_id == id
                    ),
                    lambda id, index, value: dict(
                        connection_id=id,
                        id=index,
                        shear_distortion=value.get("panel zone shear distortion (rad)"),
                        shear_force=value.get("panel zone shear force (kN)"),
                    ),
                )
            case Type.MATERIAL_STRESS_STRAIN:
                uploader = CsvFileUploader(
                    MaterialStressStrain,
                    lambda id: delete(MaterialStressStrain).where(
                        MaterialStressStrain.material_id == id
                    ),
                    lambda id, index, value: dict(
                        material_id=id,
                        id=index,
                        stress=value.get("Sigma_true"),
                        strain=value.get("e_true"),
                    ),
                )
            case Type.RESIDUAL_STRESS_DISTRIBUTION_F1:
                uploader = CsvFileUploader(
                    ResidualStressDistributionF1,
                    lambda id: delete(ResidualStressDistributionF1).where(
                        ResidualStressDistributionF1.residual_stress_id == id
                    ),
                    lambda id, index, value: dict(
                        residual_stress_id=id,
                        id=index,
                        coordinate=value.get("coordinate"),
                        residual_stress=value.get("residual_stress"),
                    ),
                )
            case Type.RESIDUAL_STRESS_DISTRIBUTION_F2:
                uploader = CsvFileUploader(
                    ResidualStressDistributionF2,
                    lambda id: delete(ResidualStressDistributionF2).where(
                        ResidualStressDistributionF2.residual_stress_id == id
                    ),
                    lambda id, index, value: dict(
                        residual_stress_id=id,
                        id=index,
                        coordinate=value.get("coordinate"),
                        residual_stress=value.get("residual_stress"),
                    ),
                )
            case Type.RESIDUAL_STRESS_DISTRIBUTION_W1:
                uploader = CsvFileUploader(
                    ResidualStressDistributionW1,
                    lambda id: delete(ResidualStressDistributionW1).where(
                        ResidualStressDistributionW1.residual_stress_id == id
                    ),
                    lambda id, index, value: dict(
                        residual_stress_id=id,
                        id=index,
                        coordinate=value.get("coordinate"),
                        residual_stress=value.get("residual_stress"),
                    ),
                )
            case Type.RESIDUAL_STRESS_QP_COEFFICIENT:
                uploader = CsvFileUploader(
                    ResidualStressQPCoefficient,
                    lambda id: delete(ResidualStressQPCoefficient).where(
                        ResidualStressQPCoefficient.residual_stress_id == id
                    ),
                    lambda id, index, value: dict(
                        residual_stress_id=id,
                        id=index,
                        qp_coefficient=value.get("qp_coefficient"),
                    ),
                )
            case Type.HSS_COLUMN_MOMENT_ROTATION:
                uploader = CsvFileUploader(
                    HSSColumnMomentRotation,
                    lambda id: delete(HSSColumnMomentRotation).where(
                        HSSColumnMomentRotation.hss_column_id == id
                    ),
                    lambda id, index, value: dict(
                        hss_column_id=id,
                        id=index,
                        rotation=value.get("rotation (rad)"),
                        moment=value.get("moment (kN.m)"),
                    ),
                )
            case Type.DUCTILE_FRACTURE:
                uploader = TableUploader(DuctileFracture)
            case Type.DUCTILE_FRACTURE_FORCE_ELONGATION:
                uploader = CsvFileUploader(
                    DuctileFractureForceElongation,
                    lambda id: delete(DuctileFractureForceElongation).where(
                        DuctileFractureForceElongation.ductile_fracture_id == id
                    ),
                    lambda id, index, value: dict(
                        ductile_fracture_id=id,
                        id=index,
                        elongation=value.get("Elongation [mm]"),
                        load=value.get("Load [kN]"),
                    ),
                )
            case Type.DUCTILE_FRACTURE_FORCE_ELONGATION_SIMULATION:
                uploader = CsvFileUploader(
                    DuctileFractureForceElongationSimulation,
                    lambda id: delete(DuctileFractureForceElongationSimulation).where(
                        DuctileFractureForceElongationSimulation.ductile_fracture_id
                        == id
                    ),
                    lambda id, index, value: dict(
                        ductile_fracture_id=id,
                        id=index,
                        elongation=value.get("Elongation [mm]"),
                        load=value.get("Load [kN]"),
                    ),
                )
            case Type.DUCTILE_FRACTURE_FORCE_RADIAL:
                uploader = CsvFileUploader(
                    DuctileFractureForceRadial,
                    lambda id: delete(DuctileFractureForceRadial).where(
                        DuctileFractureForceRadial.ductile_fracture_id == id
                    ),
                    lambda id, index, value: dict(
                        ductile_fracture_id=id,
                        id=index,
                        elongation=value.get("Radial elongation [mm]"),
                        load=value.get("Load [kN]"),
                    ),
                )
            case Type.DUCTILE_FRACTURE_FORCE_RADIAL_SIMULATION:
                uploader = CsvFileUploader(
                    DuctileFractureForceRadialSimulation,
                    lambda id: delete(DuctileFractureForceRadialSimulation).where(
                        DuctileFractureForceRadialSimulation.ductile_fracture_id == id
                    ),
                    lambda id, index, value: dict(
                        ductile_fracture_id=id,
                        id=index,
                        elongation=value.get("Radial elongation [mm]"),
                        load=value.get("Load [kN]"),
                    ),
                )
            case Type.DUCTILE_FRACTURE_EPEQ_SIMULATION:
                uploader = CsvFileUploader(
                    DuctileFractureEpeqSimulation,
                    lambda id: delete(DuctileFractureEpeqSimulation).where(
                        DuctileFractureEpeqSimulation.ductile_fracture_id == id
                    ),
                    lambda id, index, value: dict(
                        ductile_fracture_id=id,
                        id=index,
                        elongation=value.get("Elongation [mm]"),
                        peeq=value.get("Equivalent plastic strain"),
                    ),
                )
            case Type.DUCTILE_FRACTURE_LODE_SIMULATION:
                uploader = CsvFileUploader(
                    DuctileFractureLodeSimulation,
                    lambda id: delete(DuctileFractureLodeSimulation).where(
                        DuctileFractureLodeSimulation.ductile_fracture_id == id
                    ),
                    lambda id, index, value: dict(
                        ductile_fracture_id=id,
                        id=index,
                        elongation=value.get("Elongation [mm]"),
                        lode=value.get("Lode angle"),
                    ),
                )
            case Type.DUCTILE_FRACTURE_TRIAX_SIMULATION:
                uploader = CsvFileUploader(
                    DuctileFractureTriaxSimulation,
                    lambda id: delete(DuctileFractureTriaxSimulation).where(
                        DuctileFractureTriaxSimulation.ductile_fracture_id == id
                    ),
                    lambda id, index, value: dict(
                        ductile_fracture_id=id,
                        id=index,
                        elongation=value.get("Elongation [mm]"),
                        triaxiality=value.get("Triaxiality"),
                    ),
                )
            case _:
                raise NotImplementedError(f"unknown type {input_type}")

        return uploader.upload_one(filename)
    except Exception as e:
        error_message = f"Error in upload_one: {e}"
        error(error_message)
        # Re-raise with more context
        raise Exception(f"Failed to upload {filename} as {input_type}: {str(e)}")


def get_args_all(input_type: Type, filename: str) -> List[Tuple[Type, str]]:
    """
    For ALL types (recursive):
    - ALL -> ALL_BRACE + ALL_COLUMN + ALL_CONNECTION + ...
    - ALL_BRACE -> BRACE + BRACE_DISPLACEMENT
    - ALL_COLUMN -> COLUMN + COLUMN_MEASUREMENTS

    For specific types:
    - Returns tuple of (type, filepath)
    - Handles wildcard expansion for measurement files
    """
    match input_type:
        case Type.ALL:
            return (
                get_args_all(Type.ALL_BRACE, filename)
                + get_args_all(Type.ALL_COLUMN, filename)
                + get_args_all(Type.ALL_CONNECTION, filename)
                + get_args_all(Type.ALL_MATERIAL, filename)
                + get_args_all(Type.ALL_RESIDUAL_STRESS, filename)
                + get_args_all(Type.ALL_HSS_COLUMN, filename)
                + get_args_all(Type.ALL_ECCENTRIC_BRACED_FRAME, filename)
                + get_args_all(Type.ALL_TENSILE_COUPON, filename)
                + get_args_all(Type.ALL_DUCTILE_FRACTURE, filename)
            )
        case Type.ALL_BRACE:
            root_folder = path.join(filename, "braces")
            return [
                (Type.BRACE, path.join(root_folder, "steel_braces.csv")),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "steel_braces_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.BRACE_DISPLACEMENT,
                    path.join(root_folder, "force_displacement", "*.csv"),
                ),
            ]
        case Type.ALL_COLUMN:
            root_folder = path.join(filename, "columns")
            return [
                (Type.COLUMN, path.join(root_folder, "steel_columns.csv")),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "steel_columns_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.COLUMN_AXIAL_SHORTENING,
                    path.join(
                        root_folder,
                        "axial_shortening_rotation",
                        "*.csv",
                    ),
                ),
                (
                    Type.COLUMN_MOMENT_STRONG,
                    path.join(root_folder, "moment_rotation_strong", "*.csv"),
                ),
                (
                    Type.COLUMN_MOMENT_WEAK,
                    path.join(root_folder, "moment_rotation_weak", "*.csv"),
                ),
            ]
        case Type.ALL_CONNECTION:
            root_folder = path.join(filename, "connections")
            return [
                (Type.CONNECTION, path.join(root_folder, "connections.csv")),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "connections_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.CONNECTION_BEAM,
                    path.join(root_folder, "Beam_moment_rotation", "*.csv"),
                ),
                (
                    Type.CONNECTION_BEAM_WEST,
                    path.join(
                        root_folder,
                        "Beam_moment_rotation_west",
                        "*.csv",
                    ),
                ),
                (
                    Type.CONNECTION_GLOBAL,
                    path.join(root_folder, "Global", "*.csv"),
                ),
                (
                    Type.CONNECTION_GLOBAL_WEST,
                    path.join(root_folder, "Global_west", "*.csv"),
                ),
                (
                    Type.CONNECTION_PANEL_ZONE,
                    path.join(root_folder, "Panel_zone", "*.csv"),
                ),
            ]
        case Type.ALL_MATERIAL:
            root_folder = path.join(filename, "material", "cyclic_coupons")
            return [
                (Type.MATERIAL, path.join(root_folder, "steel_material.csv")),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "steel_material_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.MATERIAL_STRESS_STRAIN,
                    path.join(root_folder, "stress_strain", "*.csv"),
                ),
            ]
        case Type.ALL_RESIDUAL_STRESS:
            root_folder = path.join(filename, "residual_stresses")
            return [
                (
                    Type.RESIDUAL_STRESS,
                    path.join(root_folder, "residual_stresses.csv"),
                ),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "residual_stresses_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.RESIDUAL_STRESS_DISTRIBUTION_F1,
                    path.join(
                        root_folder,
                        "Distributions/Distributions_F1",
                        "*.csv",
                    ),
                ),
                (
                    Type.RESIDUAL_STRESS_DISTRIBUTION_F2,
                    path.join(
                        root_folder,
                        "Distributions/Distributions_F2",
                        "*.csv",
                    ),
                ),
                (
                    Type.RESIDUAL_STRESS_DISTRIBUTION_W1,
                    path.join(
                        root_folder,
                        "Distributions/Distributions_W1",
                        "*.csv",
                    ),
                ),
                (
                    Type.RESIDUAL_STRESS_QP_COEFFICIENT,
                    path.join(root_folder, "QP_Coefficients", "*.csv"),
                ),
            ]
        case Type.ALL_HSS_COLUMN:
            root_folder = path.join(filename, "hss_columns")
            return [
                (
                    Type.HSS_COLUMN,
                    path.join(root_folder, "hss_columns.csv"),
                ),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "hss_columns_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.HSS_COLUMN_MOMENT_ROTATION,
                    path.join(root_folder, "Moment_Rotation", "*.csv"),
                ),
            ]
        case Type.ALL_ECCENTRIC_BRACED_FRAME:
            root_folder = path.join(filename, "eccentric_braced_frames")
            return [
                (
                    Type.ECCENTRIC_BRACED_FRAME,
                    path.join(root_folder, "eccentric_braced_frames.csv"),
                ),
                (
                    Type.DICTIONARY,
                    path.join(
                        root_folder, "eccentric_braced_frames_data_dictionary.csv"
                    ),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.ECCENTRIC_BRACED_FRAME_SHEAR_LINK_ANGLE,
                    path.join(root_folder, "processed_data", "*.csv"),
                ),
            ]
        case Type.ALL_TENSILE_COUPON:
            root_folder = path.join(filename, "material", "tensile_coupons")
            return [
                (Type.TENSILE_COUPON, path.join(root_folder, "tensile_coupons.csv")),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "tensile_coupons_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.TENSILE_COUPON_STRESS_STRAIN,
                    path.join(root_folder, "stress_strain", "*.csv"),
                ),
            ]
        case Type.ALL_DUCTILE_FRACTURE:
            root_folder = path.join(filename, "material", "ductile_fracture")
            return [
                (
                    Type.DUCTILE_FRACTURE,
                    path.join(root_folder, "ductile_fracture.csv"),
                ),
                (
                    Type.DICTIONARY,
                    path.join(root_folder, "ductile_fracture_data_dictionary.csv"),
                ),
                (Type.README, path.join(root_folder, "README.md")),
                (
                    Type.DUCTILE_FRACTURE_FORCE_ELONGATION,
                    path.join(root_folder, "force_elongation", "*.csv"),
                ),
                (
                    Type.DUCTILE_FRACTURE_FORCE_ELONGATION_SIMULATION,
                    path.join(root_folder, "force_elongation_simulation", "*.csv"),
                ),
                (
                    Type.DUCTILE_FRACTURE_FORCE_RADIAL,
                    path.join(root_folder, "force_radial", "*.csv"),
                ),
                (
                    Type.DUCTILE_FRACTURE_FORCE_RADIAL_SIMULATION,
                    path.join(root_folder, "force_radial_simulation", "*.csv"),
                ),
                (
                    Type.DUCTILE_FRACTURE_EPEQ_SIMULATION,
                    path.join(
                        root_folder,
                        "equivalent_plastic_strain_elongation_simulation",
                        "*.csv",
                    ),
                ),
                (
                    Type.DUCTILE_FRACTURE_LODE_SIMULATION,
                    path.join(root_folder, "lode_angle_elongation_simulation", "*.csv"),
                ),
                (
                    Type.DUCTILE_FRACTURE_TRIAX_SIMULATION,
                    path.join(
                        root_folder, "triaxiality_elongation_simulation", "*.csv"
                    ),
                ),
            ]
        case _:
            return [(input_type, filename)]


def upload_parallel(upload_args, cpu=None):
    """
    Parallel processing of uploads
    1. Creates process pool based on CPU count
    2. Initializes separate DB connections per process
    3. Distributes upload tasks across processes
    4. Collects results from all processes
    """
    n_workers = cpu if cpu is not None else get_safe_cpu_count()
    current_log_level = getLogger().level
    root_logger = getLogger()
    current_log_format = None
    if root_logger.handlers and hasattr(root_logger.handlers[0], "formatter"):
        if root_logger.handlers[0].formatter:
            current_log_format = root_logger.handlers[0].formatter._fmt

    # Longest-processing-time-first scheduling: hand out the biggest files first
    # and one at a time (chunksize=1) so a handful of huge files fan out across
    # workers instead of landing in the same starmap chunk and serializing.
    def _size(arg):
        try:
            return path.getsize(arg[1])
        except OSError:
            return 0

    upload_args = sorted(upload_args, key=_size, reverse=True)
    with get_context("spawn").Pool(
        n_workers,
        initializer=initializer,
        initargs=(current_log_level, current_log_format),
    ) as pool:
        return pool.starmap(upload_one, upload_args, chunksize=1)


def cap_series(
    args: List[Tuple[Type, str]], series_limit: int
) -> List[Tuple[Type, str]]:
    """
    Keep every main-table, dictionary and README file, but at most
    ``series_limit`` measurement files per series type. Files are considered in
    sorted order so the same exemplars survive every run.
    """
    kept: List[Tuple[Type, str]] = []
    per_type: Counter = Counter()
    for upload_type, file_path in sorted(args, key=lambda a: (a[0].value, a[1])):
        if upload_type not in SERIES_EXEMPT_TYPES:
            if per_type[upload_type] >= series_limit:
                continue
            per_type[upload_type] += 1
        kept.append((upload_type, file_path))
    return kept


def upload_all(
    input_type: Type, filenames: List[str], series_limit: Optional[int] = None
):
    """
    Main upload orchestration:
    1. Collects all (Type, filepath) tuples via get_args_all
    2. Expands wildcards into actual filenames
    3. Caps measurement files per series type when series_limit is given
    4. Splits into primary (main tables) and subsidiary (measurements) types
    5. Processes primary tables first (required for foreign key constraints)
    6. Processes subsidiary data in parallel
    """

    cpu = get_safe_cpu_count()

    info(f"Number of CPUs available: {cpu}")

    wildcard_args = [
        arg for filename in filenames for arg in get_args_all(input_type, filename)
    ]
    args = [(arg[0], filename) for arg in wildcard_args for filename in iglob(arg[1])]

    if series_limit is not None:
        args = cap_series(args, series_limit)

    primary_types = [arg for arg in args if arg[0] in PRIMARY_TYPES]
    subsidiary_types = [arg for arg in args if arg[0] not in PRIMARY_TYPES]

    primary_results = upload_parallel(primary_types, cpu) if primary_types else []
    subsidiary_results = (
        upload_parallel(subsidiary_types, cpu) if subsidiary_types else []
    )

    all_results = [
        result for result in (primary_results + subsidiary_results) if result
    ]
    info(f"Uploaded all: {all_results}")

    with Session() as session:
        recompute_count_flags(session)
        session.commit()

    return [primary_results, subsidiary_results]


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


# Run with `python -m resslab_hub.data.uploader <type> <files...>`. The guard
# matters: the parallel pool uses spawn, so children re-import this module.
if __name__ == "__main__":
    main()
