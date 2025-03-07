"""added unverified column in cmte_sponsor_docs table

Revision ID: 15703cb31545
Revises: 3fbe7672dc78
Create Date: 2025-03-07 16:41:11.108336

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15703cb31545'
down_revision = '3fbe7672dc78'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cmte_sponsor_docs', sa.Column('unverified', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cmte_sponsor_docs', 'unverified')
    # ### end Alembic commands ###
