"""added eng and thai title fields

Revision ID: ec1142598f9a
Revises: 660d14a4a74f
Create Date: 2024-10-10 14:46:44.881758

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec1142598f9a'
down_revision = '660d14a4a74f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('members', sa.Column('th_title', sa.String(), nullable=True))
    op.add_column('members', sa.Column('en_title', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('members', 'en_title')
    op.drop_column('members', 'th_title')
    # ### end Alembic commands ###
