"""
CLI for uploading csv to database
"""
import argparse
import csv
import os
from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum
from math import nan
from typing import Any, Callable, List

from sqlalchemy import create_engine, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Boolean, Float, Integer, Numeric

from data.common import CSV_READ_MODE, UTF8_ENCODING, get_abs_path
from resslab_tools.models.database import (
    Brace,
    BraceDisplacement,
    ColumnAxialShortening,
    ColumnEntity,
    ColumnMomentStrong,
    ColumnMomentWeak,
    Connection,
    ConnectionBeam,
    ConnectionBeamWest,
    ConnectionGlobal,
    ConnectionGlobalWest,
    ConnectionPanelZone,
)
from resslab_tools.utils.database import url

engine = create_engine(url, echo=False)
session = Session(engine)


class Type(Enum):
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
    BRACE = "brace"
    BRACE_DISPLACEMENT = "brace-displacement"


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
        for filename in file_paths:
            self.upload_one(filename)


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
        with open(file_path, CSV_READ_MODE, encoding=UTF8_ENCODING) as file:
            reader = csv.reader(file, strict=True)
            headers = next(reader)
            id_index = headers.index(self.id_column_key)
            ids = []
            # add new rows
            for row in reader:
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
                print(f"deleted {removed_ids}")
        session.commit()

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
        filename = self.__get_filename(file_path)
        id = filename.removeprefix(self.filename_prefix).removesuffix(
            self.filename_suffix
        )
        with open(file_path, "rt", encoding=UTF8_ENCODING) as file:
            reader = csv.reader(file, strict=True)
            next(reader)  # skip header
            session.execute(self.get_delete(id))
            for index, value in enumerate(reader):
                session.add(self.get_instance(id, index, value))
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            print(f"error: {e.orig}")

    @staticmethod
    def __get_filename(file_path: str) -> str:
        basename = os.path.basename(file_path)
        return os.path.splitext(basename)[0]


def main():
    parser = argparse.ArgumentParser(description="Upload csv files to database")
    parser.add_argument("type", type=Type, choices=list(Type))
    parser.add_argument("filenames", nargs="+", help="data input file pattern")

    args = parser.parse_args()
    input_type: Type = args.type
    filenames: List[str] = args.filenames

    print(f"Connecting to {engine.url}")

    if input_type == Type.COLUMN:
        uploader = TableUploader(ColumnEntity)
    elif input_type == Type.CONNECTION:
        uploader = TableUploader(Connection)
    elif input_type == Type.BRACE:
        uploader = TableUploader(Brace)
    elif input_type == Type.COLUMN_AXIAL_SHORTENING:
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
            filename_prefix="Columns_",
            filename_suffix="_ShorteningRotation",
        )
    elif input_type == Type.COLUMN_MOMENT_STRONG:
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
            filename_prefix="Columns_",
            filename_suffix="_MomentRotation",
        )
    elif input_type == Type.COLUMN_MOMENT_WEAK:
        uploader = CsvFileUploader(
            lambda id: delete(ColumnMomentWeak).where(ColumnMomentWeak.column_id == id),
            lambda id, index, value: ColumnMomentWeak(
                column_id=id,
                id=index,
                chord_rotation=value[0],
                moment=value[1],
            ),
            filename_prefix="Columns_",
            filename_suffix="_MomentRotation",
        )
    elif input_type == Type.CONNECTION_BEAM:
        uploader = CsvFileUploader(
            lambda id: delete(ConnectionBeam).where(ConnectionBeam.connection_id == id),
            lambda id, index, value: ConnectionBeam(
                connection_id=id,
                id=index,
                chord_rotation=value[0],
                moment=value[1],
            ),
        )
    elif input_type == Type.CONNECTION_BEAM_WEST:
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
    elif input_type == Type.CONNECTION_GLOBAL:
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
    elif input_type == Type.CONNECTION_GLOBAL_WEST:
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
    elif input_type == Type.CONNECTION_PANEL_ZONE:
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
    elif input_type == Type.BRACE_DISPLACEMENT:
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
    else:
        raise NotImplementedError(f"unknown type {input_type}")

    uploader.upload_all(filenames)


if __name__ == "__main__":
    main()
