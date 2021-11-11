"""
Databse Models
"""
from resslab_tools.services.database import Base
from sqlalchemy import Boolean, Column, Integer, String


class Connection(Base):
    """
    Connection
    """
    __tablename__ = 'connections'

    id = Column(String, primary_key=True)
    experimental_program = Column(String)
    specimen_designation = Column(String)
    beam_to_column_type = Column(String)
    beam_section = Column(String)
    column_section = Column(String)
    slab = Column(Boolean)
    north_ridge = Column(String)
    specimen_type = Column(String)
    double_plate = Column(Integer)
