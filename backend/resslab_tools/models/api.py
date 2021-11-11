"""
API Models
"""
from pydantic import BaseModel


class Connection(BaseModel):
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
