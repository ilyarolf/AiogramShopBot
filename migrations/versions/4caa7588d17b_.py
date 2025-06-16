"""empty message

Revision ID: 4caa7588d17b
Revises: 56e532f7e9ff
Create Date: 2025-06-16 14:07:51.990581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4caa7588d17b'
down_revision: Union[str, None] = '56e532f7e9ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('PRAGMA foreign_keys = 0;')
    op.execute('CREATE TABLE sqlitestudio_temp_table AS SELECT * FROM deposits;')
    with op.batch_alter_table('deposits', schema=None) as batch_op:
        batch_op.drop_column("vout")
        batch_op.drop_column("tx_id")
        batch_op.drop_column("token_name")
        batch_op.drop_column("is_withdrawn")
    op.execute('DROP TABLE sqlitestudio_temp_table;')
    op.execute('PRAGMA foreign_keys = 1;')


def downgrade() -> None:
    pass
