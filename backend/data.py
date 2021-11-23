import argparse
import csv
import os
from enum import Enum
from typing import Any, Callable, List

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from resslab_tools.models.database import ConnectionGlobal, ConnectionPanelZone
from resslab_tools.services.database import url

engine = create_engine(url, echo=False)
session = Session(engine)


class Type(Enum):
    GLOBAL = 'global'
    PANEL_ZONE = 'panel-zone'


class DataImporter():
    def __init__(self,
                 get_delete: Callable[[str], delete],
                 get_instance: Callable[[str, int, List[str]], Any]) -> None:
        self.get_delete = get_delete
        self.get_instance = get_instance

    def import_one(self, filename: str) -> None:
        filename = os.path.abspath(filename)
        print(f'import from {filename}')
        connection_id = self.get_connection_id(filename)
        with open(filename, 'rt', encoding='utf-8') as file:
            reader = csv.reader(file, strict=True)
            next(reader)  # skip header
            session.execute(
                self.get_delete(connection_id)
            )
            for index, value in enumerate(reader):
                session.add(self.get_instance(connection_id, index, value))
        session.commit()

    def import_all(self, filenames: List[str]) -> None:
        for filename in filenames:
            self.import_one(filename)

    @staticmethod
    def get_connection_id(filename: str) -> str:
        basename = os.path.basename(filename)
        return os.path.splitext(basename)[0]


def main():
    parser = argparse.ArgumentParser(
        description='Import csv files to database')
    parser.add_argument('type', type=Type, choices=list(Type))
    parser.add_argument('filenames',
                        nargs='+',
                        help='data input file pattern')

    args = parser.parse_args()
    input_type: Type = args.type
    filenames: List[str] = args.filenames

    if input_type == Type.GLOBAL:
        data_importer = DataImporter(
            lambda id: delete(ConnectionGlobal)
            .where(ConnectionGlobal.connection_id == id),
            lambda id, index, value: ConnectionGlobal(
                connection_id=id,
                id=index,
                story_drift_angle=value[0],
                actuator_force=value[1],
            ))
    elif input_type == Type.PANEL_ZONE:
        data_importer = DataImporter(
            lambda id: delete(ConnectionPanelZone)
            .where(ConnectionPanelZone.connection_id == id),
            lambda id, index, value: ConnectionPanelZone(
                connection_id=id,
                id=index,
                shear_distortion=value[0],
                shear_force=value[1],
            ))
    else:
        raise NotImplementedError(f'unknown type {input_type}')

    data_importer.import_all(filenames)


if __name__ == '__main__':
    main()
