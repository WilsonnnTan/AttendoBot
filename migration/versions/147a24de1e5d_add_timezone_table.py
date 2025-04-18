"""add timezone table

Revision ID: 147a24de1e5d
Revises: 0063e63e5c85
Create Date: 2025-04-19 03:36:04.443275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '147a24de1e5d'
down_revision: Union[str, None] = '0063e63e5c85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Timezone',
    sa.Column('guild_id', sa.BigInteger(), nullable=False),
    sa.Column('time_delta', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['guild_id'], ['guilds.guild_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('guild_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('Timezone')
    # ### end Alembic commands ###
