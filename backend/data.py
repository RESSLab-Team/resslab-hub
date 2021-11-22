import argparse
import csv
import os

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from resslab_tools.models.database import ConnectionGlobal
from resslab_tools.services.database import url

parser = argparse.ArgumentParser(description='Import csv files to database')
parser.add_argument('input_file',
                    help='data input file')
args = parser.parse_args()
input_file: str = args.input_file
input_file = os.path.abspath(input_file)

engine = create_engine(url, echo=True)
session = Session(engine)

print(f'import from {input_file}')
with open(input_file, 'r') as file:
    basename = os.path.basename(input_file)
    connection_id = os.path.splitext(basename)[0]
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
