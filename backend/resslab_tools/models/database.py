"""
Databse Models
"""
from resslab_tools.services.database import Base
from sqlalchemy import Boolean, Column, Integer, String


class Connection(Base):
    """
    Connection
    """
    __tablename__ = 'connection'

    experimental_program = Column(String, primary_key=True)
    specimen_designation = Column(String, primary_key=True)
    beam_to_column_type = Column(String)
    beam_section = Column(String)
    column_section = Column(String)
    slab = Column(Boolean)
    pre_north_ridge = Column(Boolean)
    specimen_type = Column(String)
    double_plate = Column(Integer)
