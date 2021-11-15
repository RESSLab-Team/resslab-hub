"""
API Models
"""
from pydantic import BaseModel


class ApiModel(BaseModel):
    """
    Parent class for all API models
    """
    class Config:
        orm_mode = True


class Connection(ApiModel):
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
    n_dp: int
