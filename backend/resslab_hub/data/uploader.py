"""
CLI for uploading csv to database
"""
from abc import ABC, abstractmethod
from csv import DictReader, reader
from datetime import datetime
from decimal import Decimal
from enum import Enum
from glob import iglob
from logging import error, info, warning
from math import nan
from multiprocessing import Pool, cpu_count
from os import path
from typing import Any, Callable, List, Tuple

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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from resslab_hub.data.common import get_abs_path, get_file_encoding, is_empty_row
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
from resslab_hub.models.database.hss_column import HSSColumn, HSSColumnMomentRotation
from resslab_hub.models.database.material import Material, MaterialStressStrain
from resslab_hub.models.database.residual_stress import (
    ResidualStress,
    ResidualStressDistributionF1,
    ResidualStressDistributionF2,
    ResidualStressDistributionW1,
    ResidualStressQPCoefficient,
)
from resslab_hub.utils.database import url

engine = create_engine(url, echo=False)
Session = sessionmaker(engine)


def initializer():
    """
    https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork
    """
    engine.dispose(close=False)  # type: ignore


class Type(Enum):
    ALL = "all"
    ALL_COLUMN = "all-column"
    ALL_BRACE = "all-brace"
    ALL_CONNECTION = "all-connection"
    ALL_MATERIAL = "all-material"
    ALL_RESIDUAL_STRESS = "all-residual-stress"
    ALL_HSS_COLUMN = "all-hss-column"
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


class Uploader(ABC):
    """
    Abstract class for all uploaders
    """

    @abstractmethod
    def upload_one(self, file_path: str) -> str:
        """
        Upload one file
        """


class TableUploader(Uploader):
    """
    Uploader from csv to table (csv header and table column name should match)
    """

    def __init__(self, base_model: Any, id_column_key: str = "id") -> None:
        self.base_model = base_model
        self.id_column_key = id_column_key
        self.id_column = base_model.__dict__[id_column_key]

    def upload_one(self, file_path: str) -> str:
        file_path = get_abs_path(file_path)
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
                # add new rows
                for row in csv_reader:
                    if is_empty_row(row):
                        warning("skip empty line")
                    else:
                        ids.append(row[id_index])
                        data = {
                            column.key: self.__get_value(column, headers, row)
                            for column in self.base_model.__table__.c
                        }
                        session.merge(self.base_model(**data))
                # remove outdated rows
                database_ids = [row[0] for row in session.query(self.id_column).all()]
                removed_ids = set(database_ids) - set(ids)
                if removed_ids:
                    session.execute(
                        delete(self.base_model).where(self.id_column.in_(removed_ids)),
                    )
                    warning(f"deleted {removed_ids}")
                session.commit()
                return ""
        except Exception as e:
            error_message = f"skiping {file_path} due to error {e}"
            error(error_message)
            return error_message

    @staticmethod
    def __get_value(column: Column, headers: List[str], row: List[str]) -> Any:
        index = headers.index(column.key or "")
        value = row[index]

        if value.upper() == "NA":
            if isinstance(column.type, String):
                return "Not applicable"
            return None
        if value.upper() == "NR":
            if isinstance(column.type, String):
                return "Not reported"
            return nan
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
            return datetime.strptime(value, "%d.%m.%y").date()

        return str(value)


class CsvFileUploader(Uploader):
    """
    Uploader from csv to table
    """

    def __init__(
        self,
        get_delete: Callable[[str], delete],
        get_instance: Callable[[str, int, dict[str, str]], Any],
        filename_prefix="",
        filename_suffix="",
    ) -> None:
        self.get_delete = get_delete
        self.get_instance = get_instance
        self.filename_prefix = filename_prefix
        self.filename_suffix = filename_suffix

    def upload_one(self, file_path: str) -> str:
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
                for index, value in enumerate(reader):
                    session.add(self.get_instance(id, index, value))
                try:
                    session.commit()
                    return ""
                except IntegrityError as e:
                    session.rollback()
                    raise Exception(e.orig)
        except Exception as e:
            error_message = f"skiping {file_path} due to error {e}"
            error(error_message)
            return error_message

    @staticmethod
    def __get_filename(file_path: str) -> str:
        basename = path.basename(file_path)
        return path.splitext(basename)[0]


def upload_one(input_type: Type, filename: str) -> str:
    match input_type:
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
        case Type.BRACE_DISPLACEMENT:
            uploader = CsvFileUploader(
                lambda id: delete(BraceDisplacement).where(
                    BraceDisplacement.brace_id == id
                ),
                lambda id, index, value: BraceDisplacement(
                    brace_id=id,
                    id=index,
                    displacement=value.get("Displacement [mm]"),
                    force=value.get("Force [kN]"),
                ),
            )
        case Type.COLUMN_AXIAL_SHORTENING:
            uploader = CsvFileUploader(
                lambda id: delete(ColumnAxialShortening).where(
                    ColumnAxialShortening.column_id == id
                ),
                lambda id, index, value: ColumnAxialShortening(
                    column_id=id,
                    id=index,
                    chord_rotation=value.get("Chord Rotation [rads]"),
                    axial_shortening=value.get("Axial Shortening [mm]"),
                ),
            )
        case Type.COLUMN_MOMENT_STRONG:
            uploader = CsvFileUploader(
                lambda id: delete(ColumnMomentStrong).where(
                    ColumnMomentStrong.column_id == id
                ),
                lambda id, index, value: ColumnMomentStrong(
                    column_id=id,
                    id=index,
                    chord_rotation=value.get("Chord Rotation [rads]"),
                    moment=value.get("Moment [kN-mm]"),
                ),
            )
        case Type.COLUMN_MOMENT_WEAK:
            uploader = CsvFileUploader(
                lambda id: delete(ColumnMomentWeak).where(
                    ColumnMomentWeak.column_id == id
                ),
                lambda id, index, value: ColumnMomentWeak(
                    column_id=id,
                    id=index,
                    chord_rotation=value.get("Chord Rotation [rads]"),
                    moment=value.get("Moment [kN-mm]"),
                ),
            )
        case Type.CONNECTION_BEAM:
            uploader = CsvFileUploader(
                lambda id: delete(ConnectionBeam).where(
                    ConnectionBeam.connection_id == id
                ),
                lambda id, index, value: ConnectionBeam(
                    connection_id=id,
                    id=index,
                    chord_rotation=value.get("Chord Rotation [rads]")
                    or value.get("Chrord Rotation, θ [rads]"),
                    moment=value.get("Moment [kN-mm]"),
                ),
            )
        case Type.CONNECTION_BEAM_WEST:
            uploader = CsvFileUploader(
                lambda id: delete(ConnectionBeamWest).where(
                    ConnectionBeamWest.connection_id == id
                ),
                lambda id, index, value: ConnectionBeamWest(
                    connection_id=id,
                    id=index,
                    chord_rotation=value.get("Chrord Rotation, θ [rads]"),
                    moment=value.get("Moment [kN-mm]"),
                ),
            )
        case Type.CONNECTION_GLOBAL:
            uploader = CsvFileUploader(
                lambda id: delete(ConnectionGlobal).where(
                    ConnectionGlobal.connection_id == id
                ),
                lambda id, index, value: ConnectionGlobal(
                    connection_id=id,
                    id=index,
                    story_drift_angle=value.get("Total story drift angle (rad)"),
                    actuator_force=value.get("Force in the actuator (kN)"),
                ),
            )
        case Type.CONNECTION_GLOBAL_WEST:
            uploader = CsvFileUploader(
                lambda id: delete(ConnectionGlobalWest).where(
                    ConnectionGlobalWest.connection_id == id
                ),
                lambda id, index, value: ConnectionGlobalWest(
                    connection_id=id,
                    id=index,
                    story_drift_angle=value.get("Total story drift angle (rad)"),
                    actuator_force=value.get("Force in the actuator (kN)"),
                ),
            )
        case Type.CONNECTION_PANEL_ZONE:
            uploader = CsvFileUploader(
                lambda id: delete(ConnectionPanelZone).where(
                    ConnectionPanelZone.connection_id == id
                ),
                lambda id, index, value: ConnectionPanelZone(
                    connection_id=id,
                    id=index,
                    shear_distortion=value.get("panel zone shear distortion (rad)"),
                    shear_force=value.get("panel zone shear force (kN)"),
                ),
            )
        case Type.MATERIAL_STRESS_STRAIN:
            uploader = CsvFileUploader(
                lambda id: delete(MaterialStressStrain).where(
                    MaterialStressStrain.material_id == id
                ),
                lambda id, index, value: MaterialStressStrain(
                    material_id=id,
                    id=index,
                    stress=value.get("Sigma_true"),
                    strain=value.get("e_true"),
                ),
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F1:
            uploader = CsvFileUploader(
                lambda id: delete(ResidualStressDistributionF1).where(
                    ResidualStressDistributionF1.residual_stress_id == id
                ),
                lambda id, index, value: ResidualStressDistributionF1(
                    residual_stress_id=id,
                    id=index,
                    coordinate=value.get("coordinate"),
                    residual_stress=value.get("residual_stress"),
                ),
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_F2:
            uploader = CsvFileUploader(
                lambda id: delete(ResidualStressDistributionF2).where(
                    ResidualStressDistributionF2.residual_stress_id == id
                ),
                lambda id, index, value: ResidualStressDistributionF2(
                    residual_stress_id=id,
                    id=index,
                    coordinate=value.get("coordinate"),
                    residual_stress=value.get("residual_stress"),
                ),
            )
        case Type.RESIDUAL_STRESS_DISTRIBUTION_W1:
            uploader = CsvFileUploader(
                lambda id: delete(ResidualStressDistributionW1).where(
                    ResidualStressDistributionW1.residual_stress_id == id
                ),
                lambda id, index, value: ResidualStressDistributionW1(
                    residual_stress_id=id,
                    id=index,
                    coordinate=value.get("coordinate"),
                    residual_stress=value.get("residual_stress"),
                ),
            )
        case Type.RESIDUAL_STRESS_QP_COEFFICIENT:
            uploader = CsvFileUploader(
                lambda id: delete(ResidualStressQPCoefficient).where(
                    ResidualStressQPCoefficient.residual_stress_id == id
                ),
                lambda id, index, value: ResidualStressQPCoefficient(
                    residual_stress_id=id,
                    id=index,
                    qp_coefficient=value.get("qp_coefficient"),
                ),
            )
        case Type.HSS_COLUMN_MOMENT_ROTATION:
            uploader = CsvFileUploader(
                lambda id: delete(HSSColumnMomentRotation).where(
                    HSSColumnMomentRotation.hss_column_id == id
                ),
                lambda id, index, value: HSSColumnMomentRotation(
                    hss_column_id=id,
                    id=index,
                    rotation=value.get("rotation (rad)"),
                    moment=value.get("moment (kN.m)"),
                ),
            )
        case _:
            raise NotImplementedError(f"unknown type {input_type}")

    return uploader.upload_one(filename)


def get_args_all(input_type: Type, filename: str) -> List[Tuple[Type, str]]:
    match input_type:
        case Type.ALL:
            return (
                get_args_all(Type.ALL_BRACE, filename)
                + get_args_all(Type.ALL_COLUMN, filename)
                + get_args_all(Type.ALL_CONNECTION, filename)
                + get_args_all(Type.ALL_MATERIAL, filename)
                + get_args_all(Type.ALL_RESIDUAL_STRESS, filename)
                + get_args_all(Type.ALL_HSS_COLUMN, filename)
            )
        case Type.ALL_BRACE:
            root_folder = path.join(filename, "braces")
            return [
                (Type.BRACE, path.join(root_folder, "steel_braces.csv")),
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
                    Type.COLUMN_AXIAL_SHORTENING,
                    path.join(root_folder, "axial_shortening_rotation", "*.csv"),
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
                    Type.CONNECTION_BEAM,
                    path.join(root_folder, "Beam_moment_rotation", "*.csv"),
                ),
                (
                    Type.CONNECTION_BEAM_WEST,
                    path.join(root_folder, "Beam_moment_rotation_west", "*.csv"),
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
            root_folder = path.join(filename, "material")
            return [
                (Type.MATERIAL, path.join(root_folder, "steel_material.csv")),
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
                    Type.RESIDUAL_STRESS_DISTRIBUTION_F1,
                    path.join(root_folder, "Distributions/Distributions_F1", "*.csv"),
                ),
                (
                    Type.RESIDUAL_STRESS_DISTRIBUTION_F2,
                    path.join(root_folder, "Distributions/Distributions_F2", "*.csv"),
                ),
                (
                    Type.RESIDUAL_STRESS_DISTRIBUTION_W1,
                    path.join(root_folder, "Distributions/Distributions_W1", "*.csv"),
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
                    Type.HSS_COLUMN_MOMENT_ROTATION,
                    path.join(root_folder, "Moment_Rotation", "*.csv"),
                ),
            ]
        case _:
            return [(input_type, filename)]


def upload_all(input_type: Type, filenames: List[str], cpu=cpu_count()):
    wildcard_args: List[Tuple[Type, str]] = [
        arg for filename in filenames for arg in get_args_all(input_type, filename)
    ]
    args: List[Tuple[Type, str]] = [
        (arg[0], filename) for arg in wildcard_args for filename in iglob(arg[1])
    ]

    primary_types = list(
        filter(
            lambda arg: arg[0]
            in [
                Type.BRACE,
                Type.COLUMN,
                Type.CONNECTION,
                Type.MATERIAL,
                Type.RESIDUAL_STRESS,
                Type.HSS_COLUMN,
            ],
            args,
        )
    )

    subsidiary_types = list(
        filter(
            lambda arg: arg not in primary_types,
            args,
        )
    )

    warning(f"using {cpu} processes")
    info(f"uploading {len(primary_types)} primary types")

    with Pool(cpu, initializer=initializer) as pool:
        primary_results = pool.starmap(upload_one, primary_types)

    info(f"uploading {len(subsidiary_types)} subsidiary types")

    with Pool(cpu, initializer=initializer) as pool:
        subsidiary_results = pool.starmap(upload_one, subsidiary_types)

    return [result for result in (primary_results + subsidiary_results) if result]
