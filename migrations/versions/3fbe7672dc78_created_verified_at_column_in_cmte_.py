"""created verified_at column in cmte_sponsor_requests table

Revision ID: 3fbe7672dc78
Revises: ee6a2e0c681d
Create Date: 2025-03-05 15:32:17.592357

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3fbe7672dc78'
down_revision = 'ee6a2e0c681d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cmte_sponsor_requests', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cmte_sponsor_requests', 'verified_at')
    # ### end Alembic commands ###
