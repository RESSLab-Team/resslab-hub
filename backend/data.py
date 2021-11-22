import argparse
import csv
import os
from typing import List

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from resslab_tools.models.database import ConnectionGlobal
from resslab_tools.services.database import url

engine = create_engine(url, echo=True)
session = Session(engine)


def main():
    parser = argparse.ArgumentParser(
        description='Import csv files to database')
    parser.add_argument('files',
                        nargs='+',
                        help='data input file pattern')
    args = parser.parse_args()
    files: List[str] = args.files

    for filename in files:
        import_data(filename)


def import_data(filename: str):
    filename = os.path.abspath(filename)
    basename = os.path.basename(filename)
    connection_id = os.path.splitext(basename)[0]
    print(f'import from {filename}')
    with open(filename, 'r') as file:
        reader = csv.reader(file, strict=True)
        next(reader)  # skip header
        session.execute(
            delete(ConnectionGlobal)
            .where(ConnectionGlobal.connection_id == connection_id)
        )
        for index, value in enumerate(reader):
            session.add(ConnectionGlobal(
                connection_id=connection_id,
                id=index,
                story_drift_angle=value[0],
                actuator_force=value[1],
            ))
    session.commit()


if __name__ == '__main__':
    main()
