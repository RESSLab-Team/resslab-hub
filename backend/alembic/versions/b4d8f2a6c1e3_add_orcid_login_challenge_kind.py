"""add the oauth_orcid login challenge kind

Sign in with ORCID (#250) keeps its OAuth state in auth_login_challenge, like
GitHub, with its own kind. The CHECK on ``kind`` gets the new value.

On the way down, the ORCID rows go first: they live ten minutes, and the old
CHECK would refuse them.

Revision ID: b4d8f2a6c1e3
Revises: e116b2904784
Create Date: 2026-11-10 17:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b4d8f2a6c1e3"
down_revision = "e116b2904784"
branch_labels = None
depends_on = None

TABLE = "auth_login_challenge"
CHECK = "auth_login_challenge_kind_check"


def upgrade():
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.create_check_constraint(
        CHECK, TABLE, "kind IN ('email', 'oauth_github', 'oauth_orcid')"
    )


def downgrade():
    op.execute(f"DELETE FROM {TABLE} WHERE kind = 'oauth_orcid'")
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.create_check_constraint(CHECK, TABLE, "kind IN ('email', 'oauth_github')")
