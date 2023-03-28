"""renamed the api_key field to secret

Revision ID: c7453b963b07
Revises: f702a0113814
Create Date: 2023-03-28 18:12:35.137665

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7453b963b07'
down_revision = 'f702a0113814'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('secret', sa.String(), nullable=False))
    op.drop_column('clients', '_api_key')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('_api_key', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_column('clients', 'secret')
    # ### end Alembic commands ###
