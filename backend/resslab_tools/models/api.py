"""
API Models
"""
import enum
from typing import List

from pydantic import BaseModel

from .database import Connection


class OrmModel(BaseModel):
    """
    Parent class for all API models
    """
    class Config:
        orm_mode = True


class ConnectionModel(OrmModel):
    """
    Connection
    """
    id: str
    experimental_program: str
    date: int
    specimen_designation: str
    northridge: str
    specimen_type: str
    slab: bool
    connection_type: str
    section_b: str
    section_c: str
    t_dp: float
    n_dp: int


class CountModel(BaseModel):
    """
    Count
    """
    names: List[str]
    value: int


ConnectionColumn = enum.Enum(
    'ConnectionColumn',
    {column.name: column.name for column in Connection.__table__.columns}
)
