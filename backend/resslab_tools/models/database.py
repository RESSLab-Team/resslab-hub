"""
Databse Models
"""
from resslab_tools.services.database import Base
from sqlalchemy import (BigInteger, Boolean, Column, ForeignKey, Numeric,
                        SmallInteger, String)


class Connection(Base):
    """
    Connection
    """
    __tablename__ = 'connection'

    id = Column(String, primary_key=True)
    experimental_program = Column(String, nullable=False)
    date = Column(SmallInteger, nullable=False)
    specimen_designation = Column(String, nullable=False)
    northridge = Column(String(4), nullable=False)
    specimen_type = Column(String, nullable=False)
    slab = Column(Boolean, nullable=False)
    connection_type = Column(String, nullable=False)
    section_b = Column(String, nullable=False)
    section_c = Column(String, nullable=False)
    t_dp = Column(Numeric(6, 3), nullable=False)
    n_dp = Column(SmallInteger, nullable=False)


class ConnectionGlobal(Base):
    """
    Global
    """
    __tablename__ = 'connection_global'

    connection_id = Column(String,
                           ForeignKey('connection.id'),
                           primary_key=True,
                           index=True)
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    story_drift_angle = Column(Numeric(20, 10), nullable=False)
    actuator_force = Column(Numeric(20, 10), nullable=False)
