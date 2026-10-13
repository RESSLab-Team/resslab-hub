"""Print a Mermaid ER diagram of the SQLAlchemy models, for docs/database-erd.md.

Usage (from backend/): make erd
"""

import resslab_hub.models.database  # noqa: F401 registers every table on Base.metadata
from resslab_hub.utils.database import Base


def generate_mermaid() -> str:
    metadata = Base.metadata
    lines = ["```mermaid", "erDiagram"]

    for table_name, table in sorted(metadata.tables.items()):
        lines.append(f"  {table_name} {{")
        for column in sorted(table.columns, key=lambda c: c.name):
            col_type = str(column.type).split("(")[0].replace(" ", "_")

            key = ""
            if column.primary_key:
                key = " PK"
            elif column.foreign_keys:
                key = " FK"

            is_indexed = any(
                col.name == column.name for idx in table.indexes for col in idx.columns
            )
            if is_indexed and not key:
                key += ' "indexed"'

            lines.append(f"    {col_type} {column.name}{key}")
        lines.append("  }")

    relationships = set()
    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            relationships.add(
                f'  {fk.column.table.name} ||--o{{ {table.name} : "{fk.parent.name}"'
            )

    lines.extend(sorted(relationships))
    lines.append("```")
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_mermaid())
