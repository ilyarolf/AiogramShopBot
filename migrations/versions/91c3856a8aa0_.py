"""empty message

Revision ID: 91c3856a8aa0
Revises: 43803f266c4a
Create Date: 2026-02-04 16:22:11.047432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91c3856a8aa0'
down_revision: Union[str, None] = '43803f266c4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "deposits",
        "amount",
        existing_type=sa.BigInteger(),
        type_=sa.Numeric(precision=78, scale=0),
        postgresql_using="amount::numeric",
        existing_nullable=False,
    )


def downgrade() -> None:
    pass
