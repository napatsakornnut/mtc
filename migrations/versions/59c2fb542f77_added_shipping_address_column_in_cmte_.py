"""added shipping_address column in cmte_receipt_details table

Revision ID: 59c2fb542f77
Revises: 5eb5e23731b1
Create Date: 2025-06-29 17:08:51.779236

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59c2fb542f77'
down_revision = '5eb5e23731b1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cmte_receipt_details', sa.Column('shipping_address', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cmte_receipt_details', 'shipping_address')
    # ### end Alembic commands ###
