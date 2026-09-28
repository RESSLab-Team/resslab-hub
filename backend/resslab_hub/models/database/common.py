from sqlalchemy import Float

# Plain float8: values arrive from asyncpg as Python floats. NaN is the
# "not reported" sentinel; the NaN checks in utils/common.py and models/api.py
# handle float NaN directly, so the historical asdecimal=True round-trip
# (float -> Decimal -> float on every fetched value) is not needed.
DecimalFloat = Float()
