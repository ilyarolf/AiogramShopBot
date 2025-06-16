"""empty message

Revision ID: bb1886565fe9
Revises: 4caa7588d17b
Create Date: 2025-06-16 14:09:08.219042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb1886565fe9'
down_revision: Union[str, None] = '4caa7588d17b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('PRAGMA foreign_keys = 0;')
    op.execute('CREATE TABLE sqlitestudio_temp_table AS SELECT * FROM users;')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint("check_btc_balance_positive")
        batch_op.drop_constraint("check_ltc_balance_positive")
        batch_op.drop_constraint("check_sol_balance_positive")
        batch_op.drop_constraint("check_usdt_erc20_balance_positive")
        batch_op.drop_constraint("check_usdc_erc20_balance_positive")
        batch_op.drop_constraint("check_usdt_trc20_balance_positive")
        batch_op.drop_column('seed')
        batch_op.drop_column('btc_balance')
        batch_op.drop_column('usdc_erc20_balance')
        batch_op.drop_column('btc_address')
        batch_op.drop_column('eth_address')
        batch_op.drop_column('ltc_address')
        batch_op.drop_column('ltc_balance')
        batch_op.drop_column('last_balance_refresh')
        batch_op.drop_column('usdt_trc20_balance')
        batch_op.drop_column('sol_address')
        batch_op.drop_column('usdt_erc20_balance')
        batch_op.drop_column('trx_address')
        batch_op.drop_column('sol_balance')

    op.execute('DROP TABLE sqlitestudio_temp_table;')
    op.execute('PRAGMA foreign_keys = 1;')


def downgrade() -> None:
    pass
