"""
Databse Models
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
    select,
)
from sqlalchemy.orm import column_property

from resslab_tools.services.database import Base


class ConnectionGlobal(Base):
    """
    Global
    """

    __tablename__ = "connection_global"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    story_drift_angle = Column(Numeric(20, 10), nullable=False)
    actuator_force = Column(Numeric(20, 10), nullable=False)


class ConnectionPanelZone(Base):
    """
    Panel Zone
    """

    __tablename__ = "connection_panel_zone"

    connection_id = Column(
        String, ForeignKey("connection.id"), primary_key=True, index=True
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    shear_distortion = Column(Numeric(20, 10), nullable=False)
    shear_force = Column(Numeric(20, 10), nullable=False)


class Connection(Base):
    """
    Connection
    """

    __tablename__ = "connection"

    id = Column(String, primary_key=True)
    experimental_program = Column(String, nullable=False)
    date = Column(SmallInteger, nullable=False)
    specimen_designation = Column(String, nullable=False)
    northridge = Column(String(4), nullable=False)
    specimen_type = Column(String, nullable=False)
    slab = Column(Boolean, nullable=False)
    connection_type = Column(String, nullable=False)
    section_b = Column(String, nullable=False)
    d_b = Column(Numeric(8, 4))
    steel_b = Column(String)
    section_c = Column(String, nullable=False)
    d_c = Column(Numeric(8, 4))
    t_cf = Column(Numeric(20, 10))
    t_dp = Column(Numeric(6, 3), nullable=False)
    n_dp = Column(SmallInteger, nullable=False)
    t_dp_tot = column_property(t_dp * n_dp)
    global_count = column_property(
        select(func.count(ConnectionGlobal.id))
        .where(ConnectionGlobal.connection_id == id)
        .correlate_except(ConnectionGlobal)
        .scalar_subquery()  # type: ignore
    )
    panel_zone_count = column_property(
        select(func.count(ConnectionPanelZone.id))
        .where(ConnectionPanelZone.connection_id == id)
        .correlate_except(ConnectionPanelZone)
        .scalar_subquery()  # type: ignore
    )
