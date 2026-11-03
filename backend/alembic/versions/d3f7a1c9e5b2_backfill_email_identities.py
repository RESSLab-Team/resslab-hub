"""backfill email identities

An account can hold several addresses now (#402), each one an ``email`` row in
``auth_identity``. Accounts made through GitHub before this kept their address
on ``auth_user.email`` only, with no such row. This adds the missing row, so
every verified address is listed on the account page and can be the main one.

Safe to run again: an address that already has its row is skipped. Nothing is
removed on the way down, the rows are valid either way.

Revision ID: d3f7a1c9e5b2
Revises: c8e4a2f6d901
Create Date: 2026-11-03 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d3f7a1c9e5b2"
down_revision = "c8e4a2f6d901"
branch_labels = None
depends_on = None


def upgrade():
    # ``subject`` is 255 long and ``email`` 320: a longer address cannot have
    # a row, and is left as it is.
    op.execute(
        sa.text(
            """
            INSERT INTO auth_identity
                (id, user_id, provider, subject, handle, created_at)
            SELECT gen_random_uuid(), u.id, 'email', lower(u.email),
                   lower(u.email), u.created_at
            FROM auth_user u
            WHERE u.email IS NOT NULL
              AND u.email_verified_at IS NOT NULL
              AND length(u.email) <= 255
              AND NOT EXISTS (
                  SELECT 1 FROM auth_identity i
                  WHERE i.provider = 'email' AND i.subject = lower(u.email)
              )
            ON CONFLICT (provider, subject) DO NOTHING
            """
        )
    )


def downgrade():
    pass
