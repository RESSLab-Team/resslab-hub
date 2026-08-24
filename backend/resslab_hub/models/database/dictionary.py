"""
Data-dictionary table: one row per column of each component database.

Loaded from the data repository's ``*_data_dictionary.csv`` files at upload
time; served to the frontend via ``GET /dictionary``.
"""

from sqlalchemy import Boolean, Column, SmallInteger, String, Text

from resslab_hub.utils.database import Base


class DictionaryColumn(Base):  # type: ignore
    __tablename__ = "dictionary_column"

    # Frontend DatabaseId, e.g. "braces", "cyclic", "ductile-fracture".
    database = Column(String, primary_key=True)
    column_name = Column(String, primary_key=True)
    # Row order in the source CSV, which is also the CSV header order.
    position = Column(SmallInteger, nullable=False)
    description = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    type = Column(String, nullable=False)
    example = Column(String, nullable=False)
    nullable = Column(Boolean, nullable=False)


class DatabaseReadme(Base):  # type: ignore
    """
    The contributor guide of one database: the ``README.md`` next to its
    primary CSV in the data repo, uploaded with the data so each deployment
    shows the guide that matches the data branch it serves.
    """

    __tablename__ = "database_readme"

    # Frontend DatabaseId, same key space as DictionaryColumn.database.
    database = Column(String, primary_key=True)
    # Raw markdown, rendered by the frontend.
    content = Column(Text, nullable=False)
