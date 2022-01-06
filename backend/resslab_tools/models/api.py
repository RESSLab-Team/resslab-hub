"""
API Models
"""
import enum
from decimal import Decimal
from math import isnan
from typing import List, Optional, Union

from pydantic import BaseModel, validator


class OrmModel(BaseModel):
    """
    Parent class for all API models
    """

    class Config:
        orm_mode = True


class ConnectionModel(BaseModel):
    """
    Connection
    """

    @validator("f_ybw", "f_ybf", "f_ycw", "f_ycf")
    def change_nan_to_none(cls, v):
        if v is None or isnan(v):
            return None
        return v

    id: str
    experimental_program: str
    date: int
    specimen_designation: str
    northridge: str
    specimen_type: str
    loading_protocol: str
    slab: bool
    connection_type: str
    section_b: str
    d_b: Decimal
    steel_b: str
    f_yb: Decimal
    f_ybw: Optional[Decimal]
    f_ybf: Optional[Decimal]
    section_c: str
    d_c: Decimal
    t_cf: Decimal
    steel_c: str
    f_yc: Decimal
    f_ycw: Optional[Decimal]
    f_ycf: Optional[Decimal]
    backing_bar: Optional[bool]
    t_dp: Decimal
    n_dp: int
    t_dp_tot: Decimal
    ru_rn_pl_n: Decimal
    g_max_g_y: Decimal

    global_count: int
    panel_zone_count: int


class CountModel(BaseModel):
    """
    Count
    """

    names: List[str]
    value: int


class RangeModel(BaseModel):
    """
    Range
    """

    min: Decimal
    max: Decimal


class DownloadModel(BaseModel):
    """
    DownloadModel
    """

    global_csv: str
    panel_zone_csv: str


class MatrixModel(BaseModel):
    ids: List[str]
    data: List[List[Union[Decimal, str]]]


ConnectionField = enum.Enum(
    "ConnectionField", {key: key for key in ConnectionModel.__fields__}
)

ConnectionNumberField = enum.Enum(
    "ConnectionNumberField",
    {
        key: key
        for key, field in ConnectionModel.__fields__.items()
        if field.type_ in [int, Decimal]
    },
)
