"""
API Models
"""
import enum
from decimal import Decimal
from typing import List

from pydantic import BaseModel


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
    d_b: Decimal
    steel_b: str
    section_c: str
    d_c: Decimal
    t_cf: Decimal
    t_dp: Decimal
    n_dp: int
    t_dp_tot: Decimal


class CountModel(BaseModel):
    """
    Count
    """
    names: List[str]
    value: int


ConnectionColumn = enum.Enum(
    'ConnectionColumn',
    {column: column
     for column
     in ConnectionModel.__fields__}
)
