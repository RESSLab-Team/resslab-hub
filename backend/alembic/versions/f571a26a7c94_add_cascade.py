"""

Revision ID: f571a26a7c94
Revises: 3f92f28f43da
Create Date: 2024-01-08 01:42:46.950477

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f571a26a7c94"
down_revision = "3f92f28f43da"
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing foreign key constraint
    op.drop_constraint(
        "brace_displacement_brace_id_fkey", "brace_displacement", type_="foreignkey"
    )

    # Create new foreign key constraint with ON DELETE CASCADE
    op.create_foreign_key(
        "brace_displacement_brace_id_fkey",
        "brace_displacement",
        "brace",
        ["brace_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    # For downgrade, remove the CASCADE delete and revert to the original state
    op.drop_constraint(
        "brace_displacement_brace_id_fkey", "brace_displacement", type_="foreignkey"
    )
    op.create_foreign_key(
        "brace_displacement_brace_id_fkey",
        "brace_displacement",
        "brace",
        ["brace_id"],
        ["id"],
    )
