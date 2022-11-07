"""
CLI for uploading csv to database
"""
import argparse
import csv
import logging
import os
from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum
from glob import iglob
from io import TextIOWrapper
from math import nan
from typing import Any, Callable, List

from chardet import detect
from sqlalchemy import create_engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Boolean, Float, Integer, Numeric

from data.common import ASCII_ENCODING, CSV_READ_MODE, UTF8_ENCODING, get_abs_path
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
from resslab_hub.utils.database import url

engine = create_engine(url, echo=False)
session = Session(engine)


class Type(Enum):
    ALL = "all"
    ALL_COLUMN = "all-column"
    ALL_BRACE = "all-brace"
    ALL_CONNECTION = "all-connection"
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


class Uploader(ABC):
    """
    Abstract class for all uploaders
    """

    @abstractmethod
    def upload_one(self, file_path: str) -> None:
        """
        Upload one file
        """

    def upload_all(self, file_paths: List[str]) -> None:
        """
        Upload multiple files
        """
        for file_path in file_paths:
            for filename in iglob(file_path):
                self.upload_one(filename)

    @staticmethod
    def check_file(file: TextIOWrapper) -> None:
        detection = detect(file.read().encode())
        encoding = (detection or {}).get("encoding")
        if encoding not in [UTF8_ENCODING, ASCII_ENCODING]:
            raise Exception(f"expecting utf-8 encoded file but get {encoding}")
        file.seek(0)


class TableUploader(Uploader):
    """
    Uploader from csv to table (csv header and table column name should match)
    """

    def __init__(self, base_model: Any, id_column_key: str = "id") -> None:
        self.base_model = base_model
        self.id_column_key = id_column_key
        self.id_column = base_model.__dict__[id_column_key]

    def upload_one(self, file_path: str) -> None:
        file_path = get_abs_path(file_path)
        try:
            with open(file_path, CSV_READ_MODE, encoding=UTF8_ENCODING) as file:
                self.check_file(file)
                reader = csv.reader(file, strict=True)
                headers = next(reader)
                id_index = headers.index(self.id_column_key)
                ids = []
                # add new rows
                for row in reader:
                    if all([len(value) == 0 for value in row]):
                        logging.warning("skip empty line")
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
                    logging.warning(f"deleted {removed_ids}")
            session.commit()
        except Exception as e:
            logging.error(f"skiping {file_path} due to error {e}")

    @staticmethod
    def __get_value(column: Column, headers: List[str], row: List[str]) -> Any:
        index = headers.index(column.key or "")
        value = row[index]
        if value.upper() == "NA":
            return None
        if value.upper() == "NR":
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
        return str(value)


class CsvFileUploader(Uploader):
    """
    Uploader from csv to table
    """

    def __init__(
        self,
        get_delete: Callable[[str], delete],
        get_instance: Callable[[str, int, List[str]], Any],
        filename_prefix="",
        filename_suffix="",
    ) -> None:
        self.get_delete = get_delete
        self.get_instance = get_instance
        self.filename_prefix = filename_prefix
        self.filename_suffix = filename_suffix

    def upload_one(self, file_path: str) -> None:
        file_path = get_abs_path(file_path)
        try:
            filename = self.__get_filename(file_path)
            id = filename.removeprefix(self.filename_prefix).removesuffix(
                self.filename_suffix
            )
            with open(file_path, "rt", encoding=UTF8_ENCODING) as file:
                self.check_file(file)
                reader = csv.reader(file, strict=True)
                next(reader)  # skip header
                session.execute(self.get_delete(id))
                for index, value in enumerate(reader):
                    session.add(self.get_instance(id, index, value))
            try:
                session.commit()
            except IntegrityError as e:
                session.rollback()
                logging.error(f"error: {e.orig}")
        except Exception as e:
            logging.error(f"skiping {file_path} due to error {e}")

    @staticmethod
    def __get_filename(file_path: str) -> str:
        basename = os.path.basename(file_path)
        return os.path.splitext(basename)[0]


def upload(input_type: Type, filenames: List[str]):
    match input_type:
        case Type.ALL:
            upload(Type.ALL_BRACE, filenames)
            upload(Type.ALL_COLUMN, filenames)
            upload(Type.ALL_CONNECTION, filenames)
            return
        case Type.ALL_BRACE:
            root_folder = os.path.join(filenames[0], "braces")
            upload(Type.BRACE, [os.path.join(root_folder, "steel_braces.csv")])
            upload(
                Type.BRACE_DISPLACEMENT,
                [os.path.join(root_folder, "force_displacement", "*.csv")],
            )
            return
        case Type.ALL_COLUMN:
            root_folder = os.path.join(filenames[0], "columns")
            upload(Type.COLUMN, [os.path.join(root_folder, "steel_columns.csv")])
            upload(
                Type.COLUMN_AXIAL_SHORTENING,
                [os.path.join(root_folder, "axial_shortening_rotation", "*.csv")],
            )
            upload(
                Type.COLUMN_MOMENT_STRONG,
                [os.path.join(root_folder, "moment_rotation_strong", "*.csv")],
            )
            upload(
                Type.COLUMN_MOMENT_WEAK,
                [os.path.join(root_folder, "moment_rotation_weak", "*.csv")],
            )
            return
        case Type.ALL_CONNECTION:
            root_folder = os.path.join(filenames[0], "connections")
            upload(Type.COLUMN, [os.path.join(root_folder, "steel_columns.csv")])
            upload(
                Type.CONNECTION_BEAM,
                [os.path.join(root_folder, "Beam_moment_rotation", "*.csv")],
            )
            upload(
                Type.CONNECTION_BEAM_WEST,
                [os.path.join(root_folder, "Beam_moment_rotation_west", "*.csv")],
            )
            upload(
                Type.CONNECTION_GLOBAL,
                [os.path.join(root_folder, "Global", "*.csv")],
            )
            upload(
                Type.CONNECTION_GLOBAL_WEST,
                [os.path.join(root_folder, "Global_west", "*.csv")],
            )
            upload(
                Type.CONNECTION_PANEL_ZONE,
                [os.path.join(root_folder, "Panel_zone", "*.csv")],
            )
            return
        case Type.BRACE:
            uploader = TableUploader(Brace)
        case Type.COLUMN:
            uploader = TableUploader(ColumnEntity)
        case Type.CONNECTION:
            uploader = TableUploader(Connection)
        case Type.BRACE_DISPLACEMENT:
            uploader = CsvFileUploader(
                lambda id: delete(BraceDisplacement).where(
                    BraceDisplacement.brace_id == id
                ),
                lambda id, index, value: BraceDisplacement(
                    brace_id=id,
                    id=index,
                    displacement=value[0],
                    force=value[1],
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
                    chord_rotation=value[0],
                    axial_shortening=value[1],
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
                    chord_rotation=value[0],
                    moment=value[1],
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
                    chord_rotation=value[0],
                    moment=value[1],
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
                    chord_rotation=value[0],
                    moment=value[1],
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
                    chord_rotation=value[0],
                    moment=value[1],
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
                    story_drift_angle=value[0],
                    actuator_force=value[1],
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
                    story_drift_angle=value[0],
                    actuator_force=value[1],
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
                    shear_distortion=value[0],
                    shear_force=value[1],
                ),
            )
        case _:
            raise NotImplementedError(f"unknown type {input_type}")

    uploader.upload_all(filenames)


def main():
    parser = argparse.ArgumentParser(description="Upload csv files to database")
    parser.add_argument("type", type=Type, choices=list(Type))
    parser.add_argument("filenames", nargs="+", help="data input file pattern")

    args = parser.parse_args()
    input_type: Type = args.type
    filenames: List[str] = args.filenames

    logging.debug(f"connecting to {engine.url}")

    upload(input_type, filenames)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
