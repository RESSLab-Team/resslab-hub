"""
API Models
"""
from decimal import Decimal
from enum import Enum
from math import isnan
from typing import List, Optional, Union

from pydantic import BaseModel, validator


def _change_nan_to_none(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is not None and isnan(v):
        return None
    return v


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
    def change_nan_to_none(cls, v) -> Optional[Decimal]:
        return _change_nan_to_none(v)

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
    electrode: str
    w: Optional[Decimal]
    h_t: Optional[Decimal]
    f_cm: Optional[Decimal]
    deck_ribs_orientation: Optional[str]
    n_dp: int
    t_dp: Decimal
    t_dp_tot: Decimal
    ru_rn_pl_n: Decimal
    ru_rn_el_m: Optional[Decimal]
    ru_rn_pl_m: Optional[Decimal]
    g_max_g_y: Decimal
    reference: str
    link: str

    beam_count: int
    beam_west_count: int
    global_count: int
    global_west_count: int
    panel_zone_count: int

    global_west_count: int
    panel_zone_count: int

    latitude: int
    longitude: int


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


class LocationModel(BaseModel):
    """
    Location
    """

    latitude: Decimal
    longitude: Decimal
    date: int
    experimental_program: str
    section_b: str
    section_c: str
    link: Optional[str]
    reference: str
    connection_type: str
    specimen_type: str


class MatrixModel(BaseModel):
    ids: List[str]
    data: List[List[Optional[Union[Decimal, str]]]]


ConnectionField = Enum(
    "ConnectionField",
    {key: key for key in ConnectionModel.__fields__},
    module=__name__,
    type=str,
)

ConnectionNumberField = Enum(
    "ConnectionNumberField",
    {
        key: key
        for key, field in ConnectionModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)


class ColumnModel(BaseModel):
    @validator("th_80")
    def change_nan_to_none(cls, v) -> Optional[Decimal]:
        return _change_nan_to_none(v)

    id: str
    experimental_program: str
    date: int
    section_c: str
    specimen_designation: str
    d_c: Decimal
    h_over_t_cw: Decimal
    b_f_over_t_cf: Decimal
    l_b_over_r_yc: Decimal
    steel_c: str
    f_ymf: int
    f_ymw: int
    f_yn: int
    boundary_condition: str
    lateral_lp: str
    direction_lp: str
    axis_of_bending: str
    axial_lp: str
    p_g_over_p_ym: Decimal
    th_80: Optional[Decimal]
    reference: str
    link: str

    built_up: bool
    axial_shortening_count: int
    moment_strong_count: int
    moment_weak_count: int


ColumnField = Enum(
    "ColumnField",
    {key: key for key in ColumnModel.__fields__},
    module=__name__,
    type=str,
)

ColumnNumberField = Enum(
    "ColumnNumberField",
    {
        key: key
        for key, field in ColumnModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)


class BraceModel(BaseModel):
    id: str
    investigator: str
    specimen_ID: str
    date: int
    cross_section_shape: str
    cross_section_size: str
    area: Decimal
    d_br: Decimal
    t_br: Decimal
    steel: str
    f_yn: Decimal
    fy_m: Optional[Decimal]
    f_um: Optional[Decimal]
    boundary_condition: str
    t_t: Optional[Decimal]
    steel_gp: Optional[str]
    f_yn_gp: Optional[Decimal]
    f_ym_gp: Optional[Decimal]
    f_um_gp: Optional[Decimal]
    reinforcement_pl: Optional[str]
    loading_protocol: str
    kl_r: Decimal
    reference: str
    link: str

    displacement_count: int


BraceField = Enum(
    "BraceField",
    {key: key for key in BraceModel.__fields__},
    module=__name__,
    type=str,
)

BraceNumberField = Enum(
    "BraceNumberField",
    {
        key: key
        for key, field in BraceModel.__fields__.items()
        if field.type_ in [Decimal, int]
    },
    module=__name__,
    type=str,
)
