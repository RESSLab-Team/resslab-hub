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
    specimen_designation: str
    beam_to_column_type: str
    beam_section: str
    column_section: str
    slab: bool
    north_ridge: str
    specimen_type: str
    double_plate: int
