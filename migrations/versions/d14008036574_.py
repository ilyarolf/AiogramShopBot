"""empty message

Revision ID: d14008036574
Revises: f4a4986cc57f
Create Date: 2025-12-17 19:30:05.129711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column

from enums.buy_status import BuyStatus
from enums.item_type import ItemType

# revision identifiers, used by Alembic.
revision: str = 'd14008036574'
down_revision: Union[str, None] = 'f4a4986cc57f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("PRAGMA foreign_keys=0;")

    item_type_enum = sa.Enum(ItemType)
    buy_status_enum = sa.Enum(BuyStatus)

    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(
            sa.Column(
                "item_type",
                item_type_enum,
                nullable=True
            )
        )

        batch_op.alter_column(
            "private_data",
            existing_type=sa.String(),
            nullable=True
        )

    items = table(
        "items",
        column("item_type", item_type_enum)
    )

    op.execute(
        items.update().values(item_type=ItemType.DIGITAL.value)
    )
    op.create_table('shipping_options',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False, unique=True),
                    sa.Column('price', sa.Float(), nullable=False),
                    sa.Column('is_disabled', sa.Boolean(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name'),
                    sa.UniqueConstraint('id')
                    )

    with op.batch_alter_table("cart_items") as batch_op:
        batch_op.add_column(
            sa.Column("item_type",
                      item_type_enum,
                      nullable=True)
        )
    cart_items = table(
        "cart_items",
        column("item_type", item_type_enum)
    )
    op.execute(
        cart_items.update().values(item_type=ItemType.DIGITAL.value)
    )

    with op.batch_alter_table("cart_items") as batch_op:
        batch_op.alter_column("item_type", nullable=False)

    with op.batch_alter_table("items") as batch_op:
        batch_op.alter_column(
            "item_type",
            nullable=False
        )

    with op.batch_alter_table("buys") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                buy_status_enum,
                nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "shipping_address",
                sa.String,
                nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "track_number",
                sa.String,
                nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "shipping_option_id",
                sa.Integer,
                nullable=True
            )
        )
        batch_op.create_foreign_key(
            constraint_name="fk_buys_shipping_option_id",
            referent_table="shipping_options",
            local_cols=['shipping_option_id'],
            remote_cols=['id'],
            ondelete="CASCADE"
        )

    buys = table(
        "buys",
        column("is_refunded", sa.Boolean),
        column("status", buy_status_enum),
    )

    op.execute(
        buys.update()
        .where(buys.c.is_refunded == sa.false())
        .values(status=BuyStatus.COMPLETED.value)
    )

    op.execute(
        buys.update()
        .where(buys.c.is_refunded == sa.true())
        .values(status=BuyStatus.REFUNDED.value)
    )

    with op.batch_alter_table("buys") as batch:
        batch.alter_column(
            "status",
            nullable=False
        )
        batch.drop_column("is_refunded")

    op.execute("PRAGMA foreign_keys=1;")


def downgrade() -> None:
    pass
