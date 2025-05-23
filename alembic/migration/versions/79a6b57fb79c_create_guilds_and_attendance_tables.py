"""create guilds and attendance tables

Revision ID: 79a6b57fb79c
Revises: 
Create Date: 2025-04-18 14:34:54.142871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79a6b57fb79c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('guilds',
    sa.Column('guild_id', sa.BigInteger(), nullable=False),
    sa.Column('form_url', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('guild_id')
    )
    op.create_table('attendances',
    sa.Column('guild_id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['guild_id'], ['guilds.guild_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('guild_id', 'user_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('attendances')
    op.drop_table('guilds')
    # ### end Alembic commands ###
