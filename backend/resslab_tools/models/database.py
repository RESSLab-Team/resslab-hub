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
    date = Column(Integer)
    specimen_designation = Column(String)
    northridge = Column(String)
    specimen_type = Column(String)
    slab = Column(Boolean)
    connection_type = Column(String)
    section_b = Column(String)
    section_c = Column(String)
    n_dp = Column(Integer)
